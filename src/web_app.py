import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import shutil

# Import existing logic
from recon_engine import ReconEngine
from models import ReconConfig

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'datatoolkit_uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

def get_session_dir():
    """Get or create a unique directory for the current session."""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(8)
    
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/reconcile', methods=['GET', 'POST'])
def reconcile_start():
    if request.method == 'POST':
        # Handle file uploads
        if 'source_a' not in request.files or 'source_b' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file_a = request.files['source_a']
        file_b = request.files['source_b']
        
        if file_a.filename == '' or file_b.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file_a and file_b:
            session_dir = get_session_dir()
            
            # Save files
            path_a = os.path.join(session_dir, secure_filename(file_a.filename))
            path_b = os.path.join(session_dir, secure_filename(file_b.filename))
            file_a.save(path_a)
            file_b.save(path_b)
            
            session['path_a'] = path_a
            session['path_b'] = path_b
            
            return redirect(url_for('reconcile_config'))
            
    return render_template('reconcile_upload.html')

@app.route('/reconcile/config', methods=['GET', 'POST'])
def reconcile_config():
    if 'path_a' not in session or 'path_b' not in session:
        return redirect(url_for('reconcile_start'))
        
    engine = ReconEngine()
    try:
        # Load files to get columns
        cols_a = engine.load_csv(session['path_a'], "source_a")
        cols_b = engine.load_csv(session['path_b'], "source_b")
        
        # Identify common columns for match key
        common_cols = list(set(cols_a).intersection(set(cols_b)))
        
        if request.method == 'POST':
            # Process configuration
            config_data = {
                'match_key': request.form.get('match_key'),
                'tolerance': float(request.form.get('tolerance', 0.0)),
                'date_col_a': request.form.get('date_col_a'),
                'date_col_b': request.form.get('date_col_b'),
                'amount_col_a': request.form.get('amount_col_a'),
                'amount_col_b': request.form.get('amount_col_b'),
                'desc_col_a': request.form.get('desc_col_a'),
                'desc_col_b': request.form.get('desc_col_b')
            }
            
            # Store config in session
            session['config'] = config_data
            return redirect(url_for('reconcile_run'))
            
        return render_template('reconcile_config.html', 
                             cols_a=cols_a, 
                             cols_b=cols_b, 
                             common_cols=common_cols)
                             
    except Exception as e:
        flash(f"Error loading files: {str(e)}")
        return redirect(url_for('reconcile_start'))
    finally:
        engine.close()

@app.route('/reconcile/run')
def reconcile_run():
    if 'path_a' not in session or 'config' not in session:
        return redirect(url_for('reconcile_start'))
        
    engine = ReconEngine()
    try:
        # Re-load everything
        engine.load_csv(session['path_a'], "source_a")
        engine.load_csv(session['path_b'], "source_b")
        
        cfg = session['config']
        
        # Clean amounts
        if cfg['amount_col_a']:
            engine.clean_amount_column("source_a", cfg['amount_col_a'])
        if cfg['amount_col_b']:
            engine.clean_amount_column("source_b", cfg['amount_col_b'])
            
        # Clean dates
        if cfg['date_col_a']:
            engine.clean_date_column("source_a", cfg['date_col_a'])
        if cfg['date_col_b']:
            engine.clean_date_column("source_b", cfg['date_col_b'])
            
        # Create config object
        recon_config = ReconConfig(
            source_a_path=session['path_a'],
            source_b_path=session['path_b'],
            output_dir=get_session_dir(), # Temp output
            match_key=cfg['match_key'],
            amount_tolerance=cfg['tolerance'],
            date_col_a=cfg['date_col_a'],
            date_col_b=cfg['date_col_b'],
            amount_col_a=cfg['amount_col_a'],
            amount_col_b=cfg['amount_col_b'],
            description_col_a=cfg['desc_col_a'] if cfg['desc_col_a'] != 'None' else None,
            description_col_b=cfg['desc_col_b'] if cfg['desc_col_b'] != 'None' else None
        )
        
        result = engine.reconcile(recon_config)
        session['result_summary'] = {
            'exact_matches': result.summary.exact_matches,
            'matches_with_date_note': result.summary.matches_with_date_note,
            'amount_variances': result.summary.amount_variances,
            'missing_in_b': result.summary.missing_in_b,
            'missing_in_a': result.summary.missing_in_a
        }
        
        # Get preview data (first 10 rows of each)
        previews = {}
        tables = ["exact_matches", "matches_with_date_note", "amount_variances", "missing_in_b", "missing_in_a"]
        for table in tables:
            cols = engine.get_result_columns(table)
            rows = engine.get_results(table, limit=10)
            previews[table] = {'cols': cols, 'rows': rows}
            
        return render_template('reconcile_results.html', 
                             summary=result.summary,
                             previews=previews)
                             
    except Exception as e:
        flash(f"Error running reconciliation: {str(e)}")
        return redirect(url_for('reconcile_config'))
    finally:
        engine.close()

# ==========================================
# DATA CLEANER
# ==========================================

@app.route('/clean', methods=['GET', 'POST'])
def clean_start():
    if request.method == 'POST':
        if 'input_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file = request.files['input_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file:
            session_dir = get_session_dir()
            path = os.path.join(session_dir, secure_filename(file.filename))
            file.save(path)
            
            session['clean_file_path'] = path
            return redirect(url_for('clean_config'))
            
    return render_template('clean_upload.html')

@app.route('/clean/config', methods=['GET', 'POST'])
def clean_config():
    if 'clean_file_path' not in session:
        return redirect(url_for('clean_start'))
        
    engine = ReconEngine()
    try:
        # Load to get columns
        cols = engine.load_csv(session['clean_file_path'], "input_data")
        
        if request.method == 'POST':
            # Process Form
            configs = []
            for col in cols:
                # Check for Include
                if request.form.get(f'include_{col}'):
                    configs.append({
                        'name': col,
                        'type': request.form.get(f'type_{col}'),
                        'format': request.form.get(f'format_{col}')
                    })
            
            # Store cleanup actions
            session['clean_config'] = configs
            return redirect(url_for('clean_run'))
            
        return render_template('clean_config.html', columns=cols)
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('clean_start'))
    finally:
        engine.close()

@app.route('/clean/run')
def clean_run():
    if 'clean_file_path' not in session or 'clean_config' not in session:
        return redirect(url_for('clean_start'))
        
    engine = ReconEngine()
    try:
        # Load
        engine.load_csv(session['clean_file_path'], "input_data")
        
        # Create workspace
        engine.conn.execute("CREATE OR REPLACE TABLE cleaning_workspace AS SELECT * FROM input_data")
        
        configs = session['clean_config']
        
        # Apply Clean Operations
        for cfg in configs:
            col = cfg['name']
            ctype = cfg['type']
            fmt = cfg['format']
            
            if ctype == 'Number':
                engine.clean_amount_column("cleaning_workspace", col)
                if fmt:
                    precision = len(fmt.split('.')[-1]) if '.' in fmt else 0
                    engine.format_number_output("cleaning_workspace", col, precision)
            elif ctype == 'Date':
                engine.clean_date_column("cleaning_workspace", col)
                if fmt:
                    engine.format_date_output("cleaning_workspace", col, fmt)
            elif ctype == 'Boolean':
                engine.clean_boolean_column("cleaning_workspace", col)
        
        # Select Output Columns
        included_cols = [c['name'] for c in configs]
        engine.select_columns("cleaning_workspace", included_cols, "cleaned_output")
        
        # Save Result for Download
        output_path = os.path.join(get_session_dir(), 'cleaned_data.csv')
        engine.export_table("cleaned_output", output_path)
        
        # Get Preview
        rows = engine.get_results("cleaned_output", limit=50)
        
        return render_template('clean_results.html', columns=included_cols, rows=rows)
        
    except Exception as e:
        flash(f"Error cleaning data: {str(e)}")
        return redirect(url_for('clean_config'))
    finally:
        engine.close()

# ==========================================
# DATA AGGREGATOR
# ==========================================

@app.route('/aggregate', methods=['GET', 'POST'])
def aggregate_start():
    if request.method == 'POST':
        if 'input_files' not in request.files:
            flash('No files selected')
            return redirect(request.url)
            
        files = request.files.getlist('input_files')
        if not files or files[0].filename == '':
            flash('No files selected')
            return redirect(request.url)
        
        session_dir = get_session_dir()
        file_paths = []
        
        for file in files:
            path = os.path.join(session_dir, secure_filename(file.filename))
            file.save(path)
            file_paths.append(path)
            
        session['agg_paths'] = file_paths
        return redirect(url_for('aggregate_config'))
            
    return render_template('aggregate_upload.html')

@app.route('/aggregate/config', methods=['GET', 'POST'])
def aggregate_config():
    if 'agg_paths' not in session:
        return redirect(url_for('aggregate_start'))
        
    engine = ReconEngine()
    try:
        # Validate Compatibility
        paths = session['agg_paths']
        tables = []
        cols = []
        
        for i, path in enumerate(paths):
            tname = f"agg_file_{i}"
            file_cols = engine.load_csv(path, tname)
            tables.append(tname)
            if i == 0:
                cols = file_cols
            
            # Note: For simplicity in Web V1, we skip strict schema checking display mismatch errors 
            # effectively (engine will error on UNION if mismatch, which we catch below).
        
        # Check union validity by trying it
        try:
            engine.union_tables(tables, "combined_temp", validate=True)
        except ValueError as e:
            flash(f"Schema Mismatch: {str(e)}")
            return redirect(url_for('aggregate_start'))
            
        total_rows = engine.get_row_count("combined_temp")
        
        if request.method == 'POST':
            # Save config
            session['agg_config'] = {
                'primary_group': request.form.get('primary_group'),
                'sum_col': request.form.get('sum_col'),
                'sort_by': request.form.get('sort_by'),
                'additional_groups': [k.replace('group_', '') for k in request.form if k.startswith('group_')]
            }
            return redirect(url_for('aggregate_run'))
            
        return render_template('aggregate_config.html', 
                             columns=cols, 
                             file_count=len(paths), 
                             total_rows=total_rows)
                             
    except Exception as e:
        flash(f"Error loading files: {str(e)}")
        return redirect(url_for('aggregate_start'))
    finally:
        engine.close()

@app.route('/aggregate/run')
def aggregate_run():
    if 'agg_config' not in session or 'agg_paths' not in session:
        return redirect(url_for('aggregate_start'))
    
    engine = ReconEngine()
    try:
        # Load and Union
        paths = session['agg_paths']
        tables = []
        for i, path in enumerate(paths):
            tname = f"f_{i}"
            engine.load_csv(path, tname)
            tables.append(tname)
            
        engine.union_tables(tables, "combined_data")
        
        cfg = session['agg_config']
        group_cols = [cfg['primary_group']] + cfg['additional_groups']
        # Dedup check
        group_cols = list(dict.fromkeys(group_cols))
        
        # Sort Logic
        if cfg['sort_by'] == 'total':
            order = "total_amount DESC"
        elif cfg['sort_by'] == 'count':
            order = "record_count DESC"
        else:
            order = f'"{cfg["primary_group"]}" ASC'
            
        result = engine.aggregate_data(
            "combined_data",
            group_cols,
            cfg['sum_col'],
            "final_agg",
            order
        )
        
        # Export
        output_path = os.path.join(get_session_dir(), 'aggregated_results.csv')
        engine.export_table("final_agg", output_path)
        
        # Preview
        rows = engine.get_results("final_agg", limit=100)
        cols = engine.get_columns("final_agg")
        
        return render_template('aggregate_results.html', 
                             rows=rows, 
                             columns=cols,
                             grand_total=result['grand_total'],
                             total_records=result['total_records'])
                             
    except Exception as e:
        flash(f"Aggregation Error: {str(e)}")
        return redirect(url_for('aggregate_config'))
    finally:
        engine.close()

# ==========================================
# DATA ANALYZER
# ==========================================

@app.route('/analyze', methods=['GET', 'POST'])
def analyze_start():
    if request.method == 'POST':
        file = request.files.get('input_file')
        if not file or file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        session_dir = get_session_dir()
        path = os.path.join(session_dir, secure_filename(file.filename))
        file.save(path)
        
        session['analyze_file'] = path
        session['filters'] = [] # Reset filters
        session['combine_mode'] = 'OR'
        
        return redirect(url_for('analyze_dashboard'))
        
    return render_template('analyze_upload.html')

@app.route('/analyze/dashboard')
def analyze_dashboard():
    if 'analyze_file' not in session:
        return redirect(url_for('analyze_start'))
        
    engine = ReconEngine()
    try:
        # Load Data
        engine.load_csv(session['analyze_file'], "input_data")
        cols = engine.get_columns("input_data")
        
        # Set Default Stat Column if not set
        if 'stat_col' not in session:
            # Try to find amount column
            found = False
            for c in cols:
                if 'am' in c.lower() or 'pr' in c.lower() or 'val' in c.lower():
                    session['stat_col'] = c
                    found = True
                    break
            if not found:
                session['stat_col'] = cols[0]
                
        # Apply Filters
        filters = session.get('filters', [])
        mode = session.get('combine_mode', 'OR')
        
        conditions = []
        for f in filters:
            cond = {'column': f['column']}
            if f['filter_type'] == 'text':
                cond['operator'] = 'contains'
                cond['value'] = f['min_val']
            else:
                cond['operator'] = 'between'
                # Ensure numbers are floats
                if f['filter_type'] == 'amount':
                    cond['value'] = [float(f['min_val']), float(f['max_val'])]
                else: 
                     cond['value'] = [f['min_val'], f['max_val']]
            conditions.append(cond)
            
        row_count = engine.filter_data("input_data", conditions, "filtered_data", mode)
        
        # Get Stats
        stats = {}
        if session['stat_col']:
            stats = engine.get_statistics("filtered_data", session['stat_col'])
            
        # Get Preview
        rows = engine.get_results("filtered_data", limit=50)
        
        # Prepare export for download link
        if row_count > 0:
            out_path = os.path.join(get_session_dir(), 'filtered_data.csv')
            engine.export_table("filtered_data", out_path)
        
        return render_template('analyze_dashboard.html',
                             columns=cols,
                             filters=filters,
                             combine_mode=mode,
                             stat_col=session['stat_col'],
                             stats=stats,
                             rows=rows,
                             row_count=row_count)
                             
    except Exception as e:
        flash(f"Analysis Error: {str(e)}")
        return redirect(url_for('analyze_start'))
    finally:
        engine.close()

@app.route('/analyze/add_filter', methods=['POST'])
def analyze_add_filter():
    filters = session.get('filters', [])
    filters.append({
        'column': request.form.get('column'),
        'filter_type': request.form.get('type'),
        'min_val': request.form.get('min_val'),
        'max_val': request.form.get('max_val')
    })
    session['filters'] = filters
    return redirect(url_for('analyze_dashboard'))

@app.route('/analyze/remove_filter/<int:index>')
def analyze_remove_filter(index):
    filters = session.get('filters', [])
    if 0 <= index < len(filters):
        filters.pop(index)
        session['filters'] = filters
    return redirect(url_for('analyze_dashboard'))

@app.route('/analyze/clear_filters')
def analyze_clear_filters():
    session['filters'] = []
    return redirect(url_for('analyze_dashboard'))

@app.route('/analyze/set_mode', methods=['POST'])
def analyze_set_mode():
    session['combine_mode'] = request.form.get('mode')
    return redirect(url_for('analyze_dashboard'))

@app.route('/analyze/set_stat_col', methods=['POST'])
def analyze_set_stat_col():
    session['stat_col'] = request.form.get('stat_col')
    return redirect(url_for('analyze_dashboard'))

# ==========================================
# UTILS
# ==========================================

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a file from the session directory."""
    directory = get_session_dir()
    return send_file(os.path.join(directory, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
