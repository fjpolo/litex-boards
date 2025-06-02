// This is your Verilog module that implements the Wishbone slave
// and potentially a Wishbone master.
module wbVectorUnit #(
    parameter DATA_WIDTH = 32
)(
    input  wire                 i_clk,
    input  wire                 i_rst,

    // Wishbone SLAVE B4 Interface (CPU -> Vector Unit registers)
    input  wire                 wb_s_cyc_i,    // Cycle valid
    input  wire                 wb_s_stb_i,    // Strobe (address/data valid)
    input  wire                 wb_s_we_i,     // Write enable (1 for write, 0 for read)
    input  wire [31:0]          wb_s_adr_i,    // Address (byte address)
    input  wire [DATA_WIDTH-1:0] wb_s_dat_w_i,  // Write data
    input  wire [DATA_WIDTH/8-1:0] wb_s_sel_i,  // Byte select

    output wire                 wb_s_ack_o,    // Acknowledge
    output wire [DATA_WIDTH-1:0] wb_s_dat_r_o,  // Read data
    output wire                 wb_s_err_o,    // Error

    // Wishbone MASTER B4 Interface (Vector Unit -> Main Memory)
    output wire                 wb_m_cyc_o,    // Cycle valid
    output wire                 wb_m_stb_o,    // Strobe (address/data valid)
    output wire                 wb_m_we_o,     // Write enable
    output wire [31:0]          wb_m_adr_o,    // Address
    output wire [DATA_WIDTH-1:0] wb_m_dat_w_o,  // Write data
    output wire [DATA_WIDTH/8-1:0] wb_m_sel_o,  // Byte select

    input  wire                 wb_m_ack_i,    // Acknowledge
    input  wire [DATA_WIDTH-1:0] wb_m_dat_r_i,  // Read data
    input  wire                 wb_m_err_i,    // Error

    // Example direct output (if you still want this exposed)
    output wire [31:0]          o_status
);

    // Internal registers of the Vector Unit accessible via Wishbone slave
    // These correspond to the addresses relative to WB_VECTOR_UNIT_BASE:
    // 0x00: status_reg
    // 0x04: control_reg
    // 0x08: address_reg
    reg [DATA_WIDTH-1:0] status_reg;
    reg [DATA_WIDTH-1:0] control_reg;
    reg [DATA_WIDTH-1:0] address_reg;

    // Default outputs for Wishbone Master (unless actively driven)
    assign wb_m_cyc_o   = 1'b0;
    assign wb_m_stb_o   = 1'b0;
    assign wb_m_we_o    = 1'b0;
    assign wb_m_adr_o   = 32'd0;
    assign wb_m_dat_w_o = 32'd0;
    assign wb_m_sel_o   = 4'b1111;

    // Wishbone Slave Acknowledge and Error
    assign wb_s_ack_o = wb_s_cyc_i & wb_s_stb_i; // Simple non-pipelined ACK
    assign wb_s_err_o = 1'b0; // No error generated for now

    // Wishbone Slave Read Data Mux
    reg [DATA_WIDTH-1:0] read_data_mux;
    always @(*) begin
        case (wb_s_adr_i[3:2]) // Use byte address 0x00, 0x04, 0x08
            2'b00: read_data_mux = status_reg;    // Address 0x00 (word 0)
            2'b01: read_data_mux = control_reg;   // Address 0x04 (word 1)
            2'b10: read_data_mux = address_reg;   // Address 0x08 (word 2)
            default: read_data_mux = {DATA_WIDTH{1'b0}}; // Default for unmapped addresses
        endcase
    end
    // Read data is valid when cycle is active, strobe is active, and it's a read operation
    assign wb_s_dat_r_o = (wb_s_cyc_i & wb_s_stb_i & ~wb_s_we_i) ? read_data_mux : {DATA_WIDTH{1'b0}};

    // Wishbone Slave Write Logic
    always @(posedge i_clk or posedge i_rst) begin
        if (i_rst) begin
            status_reg  <= {DATA_WIDTH{1'b0}};
            control_reg <= {DATA_WIDTH{1'b0}};
            address_reg <= {DATA_WIDTH{1'b0}};
        end else begin
            // Only perform write if cycle, strobe, and write enable are active
            if (wb_s_cyc_i & wb_s_stb_i & wb_s_we_i) begin
                case (wb_s_adr_i[3:2]) // Use byte address 0x00, 0x04, 0x08
                    2'b00: status_reg  <= wb_s_dat_w_i; // Write to status_reg (Address 0x00)
                    2'b01: control_reg <= wb_s_dat_w_i; // Write to control_reg (Address 0x04)
                    2'b10: address_reg <= wb_s_dat_w_i; // Write to address_reg (Address 0x08)
                    default: ; // Do nothing for unmapped write addresses
                endcase
            end
        end
    end

    // Example direct output
    assign o_status = status_reg; // Output the status_reg for external observation/debugging
endmodule
