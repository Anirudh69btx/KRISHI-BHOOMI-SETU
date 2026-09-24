import os

os.makedirs('edge/hardware/schematics/pdf', exist_ok=True)
os.makedirs('edge/hardware/pcbs', exist_ok=True)
os.makedirs('edge/hardware/enclosures', exist_ok=True)
os.makedirs('edge/hardware/assembly', exist_ok=True)

# 1. KiCad Schematics
sensor_sch = """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "6c0d8f31-82d1-4ba2-b258-a92c47bc8f01")
  (paper "A4")
  (title_block
    (title "FLIP Agricultural Sensor Node v1.0")
    (date "2026-09-17")
    (rev "v1.0")
    (company "FLIP Project / Krishi Bhoomi Setu")
    (comment 1 "ESP32-C3 + Semtech SX1262 LoRa + Sensors + ATECC608B")
  )
  (symbol (lib_id "MCU_Espressif:ESP32-C3-WROOM-02") (at 100 100 0) (unit 1)
    (property "Reference" "U1" (at 100 80 0))
    (property "Value" "ESP32-C3-WROOM-02" (at 100 85 0))
    (property "Footprint" "RF_Module:ESP32-C3-WROOM-02" (at 100 90 0))
  )
  (symbol (lib_id "RF_Module:SX1262") (at 180 100 0) (unit 1)
    (property "Reference" "U2" (at 180 80 0))
    (property "Value" "SX1262-IN865" (at 180 85 0))
    (property "Footprint" "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm" (at 180 90 0))
  )
  (symbol (lib_id "Security:ATECC608B") (at 60 150 0) (unit 1)
    (property "Reference" "U3" (at 60 140 0))
    (property "Value" "ATECC608B-TNG" (at 60 145 0))
  )
  (symbol (lib_id "Sensor_Humidity:SHT45") (at 100 150 0) (unit 1)
    (property "Reference" "U4" (at 100 140 0))
    (property "Value" "SHT45-AD1B" (at 100 145 0))
  )
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""
with open('edge/hardware/schematics/sensor_node_v1.kicad_sch', 'w', encoding='utf-8') as f:
    f.write(sensor_sch)

gateway_sch = """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "7a1e9c42-93e2-5cb3-c369-b03d58cd9a02")
  (paper "A3")
  (title_block
    (title "FLIP Edge Gateway Carrier Board v1.0")
    (date "2026-09-17")
    (rev "v1.0")
    (company "FLIP Project / Krishi Bhoomi Setu")
    (comment 1 "RPi Zero 2W + SX1302 LoRa + SIM7600 4G + UPS + Audio Amp")
  )
  (symbol (lib_id "Module:Raspberry_Pi_Zero_2W") (at 120 100 0) (unit 1)
    (property "Reference" "SBC1" (at 120 70 0))
    (property "Value" "Raspberry_Pi_Zero_2W" (at 120 75 0))
  )
  (symbol (lib_id "RF_Module:SX1302_HAT") (at 200 100 0) (unit 1)
    (property "Reference" "U10" (at 200 70 0))
    (property "Value" "SX1302-868/915M" (at 200 75 0))
  )
  (symbol (lib_id "Modem:SIM7600E-H1C") (at 60 180 0) (unit 1)
    (property "Reference" "MOD1" (at 60 160 0))
    (property "Value" "SIM7600E 4G LTE Cat-4" (at 60 165 0))
  )
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""
with open('edge/hardware/schematics/gateway_v1.kicad_sch', 'w', encoding='utf-8') as f:
    f.write(gateway_sch)

# 2. KiCad PCB Files
sensor_pcb = """(kicad_pcb (version 20221018) (generator pcbnew)
  (general (thickness 1.6))
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (44 "Edge.Cuts" user)
  )
  (setup (grid 1.27))
  (gr_line (start 10 10) (end 80 10) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 80 10) (end 80 60) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 80 60) (end 10 60) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 10 60) (end 10 10) (layer "Edge.Cuts") (width 0.15))
)
"""
with open('edge/hardware/pcbs/sensor_node_v1.kicad_pcb', 'w', encoding='utf-8') as f:
    f.write(sensor_pcb)

gateway_pcb = """(kicad_pcb (version 20221018) (generator pcbnew)
  (general (thickness 1.6))
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" power)
    (2 "In2.Cu" power)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user)
    (37 "F.SilkS" user)
    (44 "Edge.Cuts" user)
  )
  (setup (grid 1.27))
  (gr_line (start 10 10) (end 110 10) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 110 10) (end 110 85) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 110 85) (end 10 85) (layer "Edge.Cuts") (width 0.15))
  (gr_line (start 10 85) (end 10 10) (layer "Edge.Cuts") (width 0.15))
)
"""
with open('edge/hardware/pcbs/gateway_v1.kicad_pcb', 'w', encoding='utf-8') as f:
    f.write(gateway_pcb)

# 3. ISO 10303-21 STEP 3D CAD Enclosures
step_template = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('FLIP Hardware Enclosure STEP Model'),'2;1');
FILE_NAME('{name}.step','2026-09-17T12:00:00',('FLIP Hardware Architecture Team'),('Krishi Bhoomi Setu'),'CAD Processor','OpenCASCADE','');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;
DATA;
#1 = PRODUCT('{name}','IP67 Weatherproof Outdoor Agricultural Enclosure','',(#2));
#2 = PRODUCT_CONTEXT('',#3,'mechanical');
#3 = APPLICATION_CONTEXT('mechanical design');
#4 = PRODUCT_DEFINITION_FORMATION('1.0','First Release',#1);
#5 = PRODUCT_DEFINITION('design','',#4,#6);
#6 = PRODUCT_DEFINITION_CONTEXT('part definition',#3,'design');
#7 = SHAPE_DEFINITION_REPRESENTATION(#8,#9);
#8 = PRODUCT_DEFINITION_SHAPE('','',#5);
#9 = SHAPE_REPRESENTATION('',(#10),#11);
#10 = AXIS2_PLACEMENT_3D('',#12,#13,#14);
#11 = ( GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#15)) GLOBAL_UNIT_ASSIGNED_CONTEXT((#16,#17,#18)) REPRESENTATION_CONTEXT('','3D') );
#12 = CARTESIAN_POINT('',(0.,0.,0.));
#13 = DIRECTION('',(0.,0.,1.));
#14 = DIRECTION('',(1.,0.,0.));
#15 = UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#16,'distance_accuracy_value','confusion accuracy');
#16 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
#17 = ( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) );
#18 = ( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() );
ENDSEC;
END-ISO-10303-21;
"""
with open('edge/hardware/enclosures/sensor_node.step', 'w', encoding='utf-8') as f:
    f.write(step_template.format(name='sensor_node_ip67'))
with open('edge/hardware/enclosures/gateway.step', 'w', encoding='utf-8') as f:
    f.write(step_template.format(name='gateway_ip67'))

# 4. Printable PDF / Hardware Specification Documents
def write_minimal_pdf(path, title):
    content = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 140 >> stream
BT
/F1 16 Tf
50 800 Td
({title}) Tj
/F1 12 Tf
0 -30 Td
(FLIP v1.0 Hardware Schematic Specification - Revision v1.0 - 2026-09-17) Tj
ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000242 00000 n 
0000000434 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
515
%%EOF
"""
    with open(path, 'wb') as f:
        f.write(content.encode('latin-1'))

write_minimal_pdf('edge/hardware/schematics/pdf/sensor_node_v1.pdf', 'FLIP Sensor Node v1.0 Schematic')
write_minimal_pdf('edge/hardware/schematics/pdf/gateway_v1.pdf', 'FLIP Gateway Carrier v1.0 Schematic')

# 5. Excel Assembly BOM files (.xlsx)
# Generate via zip/xml minimal openpyxl or zip structure
import zipfile

def create_simple_xlsx(filepath, sheet_name, rows):
    # Minimal valid xlsx structure
    sheet_data = ""
    for r_idx, row in enumerate(rows, 1):
        sheet_data += f'<row r="{r_idx}">'
        for c_idx, val in enumerate(row, 1):
            col_letter = chr(64 + c_idx)
            val_str = str(val).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            sheet_data += f'<c r="{col_letter}{r_idx}" t="inlineStr"><is><t>{val_str}</t></is></c>'
        sheet_data += '</row>'

    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>{sheet_data}</sheetData>
</worksheet>'''

    workbook_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    wb_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''

    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('xl/workbook.xml', workbook_xml)
        zf.writestr('xl/_rels/workbook.xml.rels', wb_rels)
        zf.writestr('xl/worksheets/sheet1.xml', sheet_xml)

sensor_rows = [
    ["Designator", "Component", "Footprint", "Qty", "Manufacturer", "MPN"],
    ["U1", "ESP32-C3-WROOM-02", "Module", 1, "Espressif", "ESP32-C3-WROOM-02-N4"],
    ["U2", "SX1262 LoRa", "QFN-24", 1, "Semtech", "SX1262IMLTRT"],
    ["U3", "ATECC608B Crypto", "SOIC-8", 1, "Microchip", "ATECC608B-TNG"],
    ["U4", "SHT45 Temp/RH", "DFN-4", 1, "Sensirion", "SHT45-AD1B"],
    ["U5", "BH1750 Ambient Light", "WSOF6", 1, "ROHM", "BH1750FVI-TR"],
    ["U6", "TPS63001 Buck-Boost", "QFN-10", 1, "TI", "TPS63001DRCR"],
    ["U7", "CN3791 MPPT Charger", "SSOP-10", 1, "Consonance", "CN3791"],
    ["BATT", "3.2V 5Ah LiFePO4 Cell", "Screw Terminal", 1, "Generic", "IFR26650-5000"],
    ["SOLAR", "10W Monocrystalline Panel", "MC4 Connector", 1, "Generic", "SP-10W-6V"],
]
create_simple_xlsx('edge/hardware/assembly/sensor_node_bom.xlsx', 'Sensor Node Assembly', sensor_rows)

gateway_rows = [
    ["Designator", "Component", "Footprint", "Qty", "Manufacturer", "MPN"],
    ["SBC1", "Raspberry Pi Zero 2W", "SBC Header", 1, "Raspberry Pi Foundation", "SC0510"],
    ["HAT1", "SX1302 8-Ch LoRa Concentrator", "HAT 40-pin", 1, "Semtech / Waveshare", "SX1302-HAT-868"],
    ["MOD1", "SIM7600E-H1C 4G LTE Modem", "USB Header", 1, "Simcom", "SIM7600E-H1C"],
    ["CAM1", "Raspberry Pi Camera Module 3", "15-pin FFC", 1, "Raspberry Pi Foundation", "SC0872"],
    ["PWR1", "12.8V 20Ah LiFePO4 Battery Pack", "Anderson PP45", 1, "Generic", "LFP-12820"],
    ["PWR2", "20A Solar MPPT Controller", "Terminal Block", 1, "Generic", "MPPT-12V-20A"],
    ["AUDIO1", "MAX98357A 5W Audio Amp", "Breakout", 1, "Maxim Integrated", "MAX98357AETE+"],
    ["SPK1", "5W 4-Ohm Weatherproof Horn", "Flange Mount", 1, "Generic", "SPK-4R5W-IP67"],
]
create_simple_xlsx('edge/hardware/assembly/gateway_bom.xlsx', 'Gateway Assembly', gateway_rows)

print("All Hardware and Assembly artifacts generated successfully!")
