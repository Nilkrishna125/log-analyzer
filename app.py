from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'please give me that extra three marks!!'

# Configurations
UPLOAD_FOLDER = 'uploads'

SCRIPT_FOLDER = 'scripts'
ALLOWED_EXTENSIONS = {'log'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check if uploaded file has .log extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home route for uploading the log file
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'logfile' not in request.files:
            flash('No file part in the request')
            return redirect(request.url)

        file = request.files['logfile']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = 'sample.log'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            base_name, _ = os.path.splitext(filepath)
            output_csv = base_name + '.csv'
            bash_script = os.path.join(SCRIPT_FOLDER, 'process_log.sh')  # Change if your script is named differently
            
            try:
                # Run bash script to process log and create CSV
                subprocess.run([bash_script, filepath, output_csv], check=True)

                # Redirect to display page
                return redirect(url_for('display_logs', csv_file=os.path.basename(output_csv)))
            except subprocess.CalledProcessError:
                flash('Error: Invalid log file format or script execution failed')
                return redirect(request.url)

    return render_template('upload.html')

# Route to display the processed log data
@app.route('/display/<csv_file>')
def display_logs(csv_file):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_file)
    if not os.path.exists(csv_path):
        flash('Processed CSV file not found')
        return redirect(url_for('upload_file'))

    df = pd.read_csv(csv_path)

    # --- Ensure correct types for filtering ---
    if 'LineId' in df.columns:
        df['LineId'] = pd.to_numeric(df['LineId'], errors='coerce')
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # --- Get search query ---
    query = request.args.get('query', '').lower()
    if query:
        df = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(query).any(), axis=1)]

    # --- Get filter inputs from query string ---
    line_from = request.args.get('line_from', type=int)
    line_to = request.args.get('line_to', type=int)
    ts_from = request.args.get('timestamp_from')
    ts_to = request.args.get('timestamp_to')

    # --- Apply Line ID filters ---
    if line_from is not None:
        df = df[df['LineId'] >= line_from]
    if line_to is not None:
        df = df[df['LineId'] <= line_to]

    # --- Apply Timestamp filters ---
    if ts_from:
        df = df[df['timestamp'] >= ts_from]
    if ts_to:
        df = df[df['timestamp'] <= ts_to]

    # --- Convert to table format for HTML ---
    table_data = df.to_dict(orient='records')
    columns = df.columns.tolist()
    
    return render_template('display.html', table=table_data, columns=columns, csv_file=csv_file)


@app.route('/visualize/<path:csv_file>', methods=['GET', 'POST'])
def visualize(csv_file):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_file)

    if not os.path.exists(csv_path):
        flash('CSV file not found for visualization')
        return redirect(url_for('upload_file'))

    df = pd.read_csv(csv_path)

    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    # Filter by date if POST
    if request.method == 'POST':
        start = request.form.get('start')
        end = request.form.get('end')
        try:
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)]
        except:
            flash('Invalid date format')

    plots = {}
    

    # 1. Events over time (line plot)
    event_counts = df.groupby(df['timestamp']).size()
    fig1, ax1 = plt.subplots()
    event_counts.plot(ax=ax1)
    ax1.set_title('Events Over Time')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Number of Events')
    output_path = os.path.join('static','plots','sample_events.png')
    fig1.savefig(output_path)
    plt.close(fig1)

    # 2. Level distribution (pie chart)
    fig2, ax2 = plt.subplots()
    df['level'].value_counts().plot.pie(autopct='%1.1f%%', ax=ax2)
    ax2.set_title('Level State Distribution')
    ax2.set_ylabel('')
    output_path = os.path.join('static','plots','sample_level.png')
    fig2.savefig(output_path)
    plt.close(fig2)

    # 3. Event code distribution (bar chart)
    fig3, ax3 = plt.subplots()
    df['eventid'].value_counts().sort_index().plot.bar(ax=ax3)
    ax3.set_title('Event Code Distribution')
    ax3.set_xlabel('Event Code')
    ax3.set_ylabel('Frequency')
    output_path = os.path.join('static','plots','sample_event_code.png')
    fig3.savefig(output_path)
    plt.close(fig3)

    return render_template('visualize.html', csv_file=csv_file)

@app.route('/filter_download/<csv_file>', methods=['GET', 'POST'])
def filter_download(csv_file):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_file)
    if not os.path.exists(csv_path):
        flash("CSV file not found.")
        return redirect(url_for('upload_file'))

    df = pd.read_csv(csv_path)

    if request.method == 'POST':
        serial_start = request.form.get('serial_start')
        serial_end = request.form.get('serial_end')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        eventid = request.form.get('eventid')
        level = request.form.get('level')

        filtered_df = df.copy()

        # Serial number filtering
        if serial_start and serial_end:
            try:
                filtered_df = filtered_df[(filtered_df['LineId'].astype(int) >= int(serial_start)) & 
                                          (filtered_df['LineId'].astype(int) <= int(serial_end))]
            except:
                flash('Invalid serial number input')

        # Timestamp filtering
        if start_time and end_time:
            try:
                filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'], errors='coerce')
                start_dt = pd.to_datetime(start_time)
                end_dt = pd.to_datetime(end_time)
                filtered_df = filtered_df[(filtered_df['timestamp'] >= start_dt) & (filtered_df['timestamp'] <= end_dt)]
            except:
                flash('Invalid timestamp input')

        # Event ID filtering
        if eventid:
            filtered_df = filtered_df[filtered_df['eventid'].astype(str).str.lower() == eventid.lower()]

        if level:
            filtered_df = filtered_df[filtered_df['level'].astype(str).str.lower() == level.lower()]

        file_path = os.path.join('uploads','filtered.csv')
        filtered_df.to_csv(file_path, index=False)

        return send_file(file_path, as_attachment=True, download_name='filtered_logs.csv', mimetype='text/csv')

    return render_template('filter_download.html', csv_file=csv_file)

@app.route('/code_your_graph/<csv_file>', methods=['GET', 'POST'])
def code_your_graph(csv_file):
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_file)
    if not os.path.exists(csv_path):
        flash('Processed CSV file not found')
        return redirect(url_for('upload_file'))

    df = pd.read_csv(csv_path)

    error_message = None
    if request.method == 'POST':
        user_code = request.form.get('python_code')  # Grab user input

        try:
            plt.close('all')
            namespace = {'df': df, 'plt': plt, 'pd': pd}
            exec(user_code, {}, namespace)

            fig = plt.gcf()
            output_path = os.path.join('static','plots','coded_plot.png')
            fig.savefig(output_path)
            plt.close(fig)

        except Exception as e:
            error_message = f"Error in your code: {str(e)}"
            flash(error_message)

    return render_template('code_your_graph.html', csv_file=csv_file)



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/exit', methods=['GET', 'POST'])
def exit_page():
    bash_script = os.path.join(SCRIPT_FOLDER, 'remove_junk.sh')
    clean_uploads = os.path.join('uploads','*')
    clean_plots = os.path.join('static','plots','*')
    subprocess.run([bash_script, clean_plots, clean_uploads], check=True)

    return 0


# Run the app
if __name__ == '__main__':
    app.run(debug=True)


