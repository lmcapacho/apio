// Code generated by Icestudio 0.13.2w202501120101
//  #START Verilator Linter rules:
/* verilator lint_off PINMISSING */
/* verilator lint_off WIDTHTRUNC */
/* verilator lint_off WIDTHEXPAND */
//  #END Verilator Linter rules
// Sun, 12 Jan 2025 00:14:33 GMT

// Testbench template

`default_nettype none
`timescale 10 ns / 1 ns


module main_tb
;
 
 // Simulation time: 100ns (10 * 10ns)
 parameter DURATION = 10;
 
 // TODO: edit the module parameters here
 // e.g. localparam constant_value = 1;
 localparam constant_Constant_0 = 4'hA;
 localparam constant_Constant_1 = 4'h5;
 
 // Input/Output
 reg Button_0;
 reg Button_1;
 wire LED0;
 wire LED1;
 wire [3:0] LEDs;
 wire LED2;
 wire LED3;
 
 // Module instance
 main #(
  .v2af3e8(constant_Constant_0),
  .v98e11a(constant_Constant_1)
 ) MAIN (
  .v17b894(Button),
  .vf8383a(Button),
  .v7b511e(LED0),
  .v6ef206(LED1),
  .v1469d9(LEDs),
  .v6898ff(LED2),
  .v1e39f8(LED3)
 );
 
 initial begin
  $dumpvars(0, main_tb);
 
  // TODO: initialize the registers here
  // e.g. value = 1;
  // e.g. #2 value = 0;
  Button_0 = 0;
  Button_1 = 0;
 
  #(DURATION) $display("End of simulation");
  $finish;
 end
 
endmodule
