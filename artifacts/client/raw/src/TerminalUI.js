// TerminalUI.js

import { Terminal } from "xterm";
import "xterm/css/xterm.css";

export class TerminalUI {
  constructor(socket) {
    this.terminal = new Terminal();

    /* You can make your terminals colorful :) */
    this.terminal.setOption("theme", {
      background: "#202B33",
      foreground: "#F5F8FA"
    });
    
    this.fitAddon = new FitAddon.FitAddon();

    this.terminal.loadAddon(this.fitAddon);
    this.terminal.loadAddon(new WebLinksAddon.WebLinksAddon());
    this.terminal.loadAddon(new SearchAddon.SearchAddon());

    this.socket = socket;
  }

  /**
   * Attach event listeners for terminal UI and socket.io client
   */
  startListening() {
    this.terminal.onData(data => this.sendInput(data));
    this.socket.on("output", data => {
      // When there is data from PTY on server, print that on Terminal.
      this.write(data);
    });
  }

  /**
   * Print something to terminal UI.
   */
  write(text) { this.terminal.write(text); }

  /**
   * Utility function to print new line on terminal.
   */
  prompt() { this.terminal.write(`\r\n`); }

  /**
   * Send whatever you type in Terminal UI to PTY process in server.
   * @param {*} input Input to send to server
   */
  sendInput(input) { this.socket.emit("input", input); }

  /**
   *
   * @param {HTMLElement} container HTMLElement where xterm can attach terminal ui instance.
   */
  attachTo(container) {
    this.terminal.open(container);
  }

  clear() {
    this.terminal.clear();
  }
}