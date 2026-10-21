const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const PORT = Number(process.env.PORT || 4321);

function readProgress() {
  const raw = fs.readFileSync(path.join(__dirname, "data", "progress.json"), "utf8");
  return JSON.parse(raw);
}

const server = http.createServer((req, res) => {
  if (req.url === "/api/progress") {
    try {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(readProgress()));
    } catch (err) {
      console.error("progress read failed", err);
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "progress_unavailable" }));
    }
    return;
  }
  const file = path.join(__dirname, "public", "index.html");
  res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  res.end(fs.readFileSync(file));
});

if (require.main === module) server.listen(PORT);
module.exports = { server };
