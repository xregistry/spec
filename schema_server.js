const http = require('http');
const fs = require('fs');
const path = require('path');

const port = 3000; // Change this to the desired port number
const directory = './'; // Change this to the directory containing the JSON files

const server = http.createServer((req, res) => {
  const filePath = path.join(directory, req.url);
  const fileExt = path.extname(filePath);
  const contentType = 'application/json';

  if (fileExt === '.json') {
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('File not found');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(data);
      }
    });
  } else {
    res.writeHead(404);
    res.end('File not found');
  }
});

server.listen(port, () => {
  console.log(`Server running on port ${port}`);
});