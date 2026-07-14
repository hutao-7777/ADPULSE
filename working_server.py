import os, shutil, http.server

DIST = r"D:\adpulse\frontend\dist"

class SPAHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        fpath = os.path.join(DIST, path.lstrip("/"))
        if os.path.isfile(fpath):
            ext = os.path.splitext(fpath)[1]
            ct = {".js":"application/javascript; charset=utf-8", ".css":"text/css; charset=utf-8", ".html":"text/html", ".svg":"image/svg+xml"}
            self.send_response(200)
            self.send_header("Content-Type", ct.get(ext, "application/octet-stream"))
            self.end_headers()
            with open(fpath, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open(os.path.join(DIST, "index.html"), "rb") as f:
            shutil.copyfileobj(f, self.wfile)
    def log_message(self, format, *args): pass

http.server.HTTPServer(("0.0.0.0", 5173), SPAHandler).serve_forever()
