// Code generated by Icestudio 0.13.2w202501120101
//  #START Verilator Linter rules:
/* verilator lint_off PINMISSING */
/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */
//  #END Verilator Linter rules
// Sun, 12 Jan 2025 00:40:01 GMT

// Testbench template

`default_nettype none
`timescale 10 ns / 1 ns


module main_tb
;
 
 // Simulation time: 100ns (10 * 10ns)
 parameter DURATION = 10;
 
 // TODO: edit the module parameters here
 // e.g. localparam constant_value = 1;
 localparam constant_LoadROM = 1;
 
 // Input/Output
 reg [1:0] btn;
 wire [7:0] LED;
 
 // Module instance
 main #(
  .vf892fe(constant_LoadROM)
 ) MAIN (
  .v2b2ed6(btn),
  .v036815(LED)
 );
 
 initial begin
  $dumpvars(0, main_tb);
 
  // TODO: initialize the registers here
  // e.g. value = 1;
  // e.g. #2 value = 0;
  btn = 0;
 
  #(DURATION) $display("End of simulation");
  $finish;
 end
 
endmodule
