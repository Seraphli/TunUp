import cgi
import os
import shlex
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HTML_TEMPLATE = """
<html>
<head>
    <title>Profile Management</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4; }
        .tabs { border: 1px solid #ccc; background: #fff; margin-top: 20px; }
        .tab-links { background: #f9f9f9; padding: 10px; cursor: pointer; display: inline-block; border-bottom: 1px solid #ccc; }
        .tab-links.active { background: #e9e9e9; border-bottom: 1px solid #fff; }
        .tab-content { display: none; padding: 20px; border-top: none; }
        .tab-content.active { display: block; }
        input, label { margin-top: 10px; display: block; width: 100%; }
        input[type="text"], input[type="file"], input[type="number"], input[type="submit"] { padding: 10px; }
    </style>
</head>
<body>
    <h1>Profile Management</h1>
    <div id="tabs">
        <div class="tab-links" onclick="openTab('Download')">Download</div>
        <div class="tab-links" onclick="openTab('Upload')">Upload</div>
    </div>
    {FORM_TEMPLATE}
    <script>
        var activeTab = "{active_tab}"; // This value is set by the server response

        function openTab(tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tablinks = document.getElementsByClassName("tab-links");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            var activeTabLink = Array.from(tablinks).find(el => el.textContent === tabName);
            if (activeTabLink) {
                activeTabLink.classList.add("active");
            }
        }

        // Initialize the active tab on page load
        document.addEventListener('DOMContentLoaded', function() {
            openTab(activeTab);
        });
    </script>
</body>
</html>
"""

FORM_TEMPLATE = """
    <div id="Download" class="tab-content">
        <form method="POST" enctype="multipart/form-data">
            <input type="hidden" name="action" value="download">
            <label for="d-name">Profile Name:</label>
            <input type="text" id="d-name" name="name" value="{download_profile_name}">
            <label for="d-url">URL:</label>
            <input type="text" id="d-url" name="url" value="{download_url}">
            <label for="d-interval">Update Interval (seconds):</label>
            <input type="number" id="d-interval" name="interval" value="{download_interval}" min="0">
            <input type="submit" value="Download">
        </form>
        <div id="download-status">{download_response_message}</div>
    </div>
    <div id="Upload" class="tab-content">
        <form method="POST" enctype="multipart/form-data">
            <input type="hidden" name="action" value="upload">
            <label for="u-name">Profile Name:</label>
            <input type="text" id="u-name" name="name" value="{upload_profile_name}">
            <label for="file">Upload File (.yml):</label>
            <input type="file" id="file" name="file" accept=".yml">
            <input type="submit" value="Upload">
        </form>
        <div id="upload-status">{upload_response_message}</div>
    </div>
"""


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        form = FORM_TEMPLATE.format(
            download_profile_name="",
            download_url="",
            download_interval="0",
            download_response_message="",
            upload_profile_name="",
            upload_response_message="",
        )
        html = HTML_TEMPLATE.replace("{FORM_TEMPLATE}", form).replace(
            "{active_tab}", "Download"
        )
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers["Content-Type"])
        if ctype == "multipart/form-data":
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers["Content-Type"],
                },
            )
            action = form.getvalue("action")
            if action == "download":
                self.handle_download(form)
            elif action == "upload":
                self.handle_upload(form)

    def handle_download(self, form):
        profile_name = form.getvalue("name")
        url = form.getvalue("url")
        interval = form.getvalue("interval", "0")

        safe_url = shlex.quote(url)
        filename = shlex.quote(profile_name + ".yml")
        command = f"curl -L {safe_url} -o {filename}"

        try:
            subprocess.run(command, shell=True, check=True)
            response_message = "File downloaded successfully."
        except subprocess.CalledProcessError as e:
            response_message = f"Error downloading file: {e}"
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            response_message = f"An unexpected error occurred: {str(e)}"
            if os.path.exists(filename):
                os.remove(filename)

        update_time = int(time.time())
        meta_filename = profile_name + ".meta.yml"
        with open(meta_filename, "w") as meta_file:
            meta_file.write(f"url: {url}\n")
            meta_file.write(f"update_time: {update_time}\n")
            meta_file.write(f"update_interval: {interval}\n")
            meta_file.write("type: download\n")

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        form_template = FORM_TEMPLATE.format(
            download_profile_name=profile_name,
            download_url=url,
            download_interval=interval,
            download_response_message=response_message,
            upload_profile_name="",
            upload_response_message="",
        )
        html = HTML_TEMPLATE.replace("{FORM_TEMPLATE}", form_template).replace(
            "{active_tab}", "Download"
        )
        self.wfile.write(html.encode("utf-8"))

    def handle_upload(self, form):
        profile_name = form.getvalue("name")
        file_item = form["file"]

        if file_item.filename and file_item.filename.endswith(".yml"):
            filename = profile_name + ".yml"
            with open(filename, "wb") as file_out:
                file_out.write(file_item.file.read())
            response_message = "File uploaded successfully."
            update_time = int(time.time())
            meta_filename = profile_name + ".meta.yml"
            with open(meta_filename, "w") as meta_file:
                meta_file.write("type: upload\n")
                meta_file.write(f"update_time: {update_time}\n")
        else:
            response_message = "Invalid file type. Only .yml files are accepted."

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        form_template = FORM_TEMPLATE.format(
            download_profile_name="",
            download_url="",
            download_interval="0",
            download_response_message="",
            upload_profile_name=profile_name,
            upload_response_message=response_message,
        )
        html = HTML_TEMPLATE.replace("{FORM_TEMPLATE}", form_template).replace(
            "{active_tab}", "Upload"
        )
        self.wfile.write(html.encode("utf-8"))


def run_server(port):
    server_address = ("", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Server running on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    run_server(port)
