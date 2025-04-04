import os, sys, logging
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import subprocess

#external python scripts
patch_script_path = "patch.py"
predict_script_path = "predict.py"
merge_script_path = "merge.py"

#upload
UPLOAD_FOLDER = '/mnt/c/Users/haslina.makmur/OneDrive - Cancer Research Malaysia/Documents/TIA_GUI/tia/uploads'
ALLOWED_EXTENSIONS = {'bif', 'svs', 'tif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/upload', methods=['GET','POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message":"No file"})
    file = request.files['file']

    if file.filename == '':
        return jsonify({"success": False, "message":"No selected file"})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            return jsonify({
                "success": True,
                "filename": filename,
                "message": "File uploaded successfully" 
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "File upload failed",
                "error": str(e)
            })
    return jsonify({"success": False, "message": "Invalid file type"})

@app.route('/patch', methods=['POST'])
def patch_file():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({
            "success": False, 
            "message": "No filename provided"
        })
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({
            "success": False, 
            "message": "File not found"
        })
    
    try:

        #file_id = os.path.splitext(filename)[0]

        result = subprocess.run(
            ["python", patch_script_path, file_path],
            capture_output=True,
            text=True,
            check=True)
        return jsonify({
            "success": True, 
            "filename": filename,
            "output": result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "message": "Patching failed",
            "error": e.stderr
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An unexpected error occurred",
            "error": str(e)
        })
    
@app.route('/merge', methods=['POST'])
def merge_file():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({
            "success": False, 
            "message": "No filename provided"
        })
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({
            "success": False, 
            "message": "File not found"
        })
    
    try:

        #file_id = os.path.splitext(filename)[0]

        result = subprocess.run(
            ["python", merge_script_path, file_path],
            capture_output=True,
            text=True,
            check=True)
        return jsonify({
            "success": True, 
            "filename": filename,
            "output": result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "message": "Merging failed",
            "error": e.stderr
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An unexpected error occurred",
            "error": str(e)
        })


if __name__ == "__main__":
    app.run(debug=True)
