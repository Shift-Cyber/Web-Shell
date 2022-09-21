import { TerminalUI } from "./TerminalUI";
import io from "socket.io-client";

const serverAddress = "http://192.168.1.51:8080";

function connectToSocket(serverAddress) {
  return new Promise(res => {
    const socket = io(serverAddress);
    res(socket);
  });
}

function startTerminal(container, socket) {
  // Create an xterm.js instance (TerminalUI class is a wrapper with some utils. Check that file for info.)
  const terminal = new TerminalUI(socket);

  // Attach created terminal to a DOM element.
  terminal.attachTo(container);

  // Ensure resize
  const resize_func = function() {
    console.log(terminal)
    terminal.fitAddon.fit()
    const dims = { cols: terminal.terminal.cols, rows: terminal.terminal.rows };
    console.log("sending new dimensions to server's pty", dims);
    socket.emit("resize", dims);
  }
  window.addEventListener('resize', resize_func);

  resize_func()

  // When terminal attached to DOM, start listening for input, output events.
  // Check TerminalUI startListening() function for details.
  terminal.startListening();
}

function start() {
  const container = document.getElementById("terminal-container");
  // Connect to socket and when it is available, start terminal.
  connectToSocket(serverAddress).then(socket => {
    startTerminal(container, socket);
  });
}

// Better to start on DOMContentLoaded. So, we know terminal-container is loaded
window.addEventListener('DOMContentLoaded', (event) => {
  start();
});
