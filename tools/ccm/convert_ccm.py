'''
simple script to transform the official CCM Excel file to another Excel file for CISO assistant framework conversion tool
'''

import openpyxl
import sys
import re
import argparse
from openpyxl.styles import numbers


def pretify_content(content):
    res = None
    stop_join = False
    for line in content.splitlines():
        if stop_join:
            res = res + '\n' + line if res else line
        else:
            res = res + ' ' + line if res else line
        if line[-1] == ':':
            stop_join = True
    return res

parser = argparse.ArgumentParser(
                    prog='convert_ccm',
                    description='convert CCM controls offical Excel file to CISO Assistant Excel file')
parser.add_argument('filename', help='name of CCM controls Excel file')
parser.add_argument('packager', help='name of packager entity')

args = parser.parse_args()
input_file_name = args.filename
packager = args.packager
output_file_name = "ccm-controls-v4.xlsx"

print("parsing", input_file_name)

# Define variable to load the dataframe
dataframe = openpyxl.load_workbook(input_file_name)
output_table = []

for tab in dataframe:
    print("parsing tab", tab.title)
    title = tab.title
    if title == "CCM":
        line=0
        eos = False
        for row in tab:
            line += 1
            if line < 4:
                continue
            (domain, title, id, specification, lite) = (r.value for r in row[0:5])
            if eos:
                library_copyright = domain # last line after end of standard
            elif lite:
                output_table.append(('x', 2, id, title, pretify_content(specification), 1 if lite else 2))
            else:
                if "End of Standard" in domain:
                    eos = True
                else:
                    (d, id) = domain.split(' - ')
                    output_table.append(('', 1, id, d, '', None))
            # if re.match(r'\d+', control):
            #     if not safeguard:
            #         safeguard_index = 0
            #         output_table.append(('', 1, control, title, description))
            #     else:
            #         safeguard_index += 1
            #         safeguard = f'{control},{safeguard_index}'
            #         maturity = 1 if ig1 else 2 if ig2 else 3
            #         output_table.append(('x', 2, safeguard, title, description, maturity))
    else:
        print(f"Ignored tab: {title}")


print("generating", output_file_name)
wb_output = openpyxl.Workbook()
ws = wb_output.active
ws.title='library_content'
ws.append(['library_urn', f'urn:{packager.lower()}:risk:library:ccm-controls-v4'])
ws.append(['library_version', '1'])
ws.append(['library_locale', 'en'])
ws.append(['library_ref_id', 'CCM-Controls-v4'])
ws.append(['library_name', 'CCM Controls v4'])
ws.append(['library_description', 'CCM Controls v4'])
ws.append(['library_copyright', library_copyright])
ws.append(['library_provider', 'CSA'])
ws.append(['library_packager', packager])
ws.append(['framework_urn', f'urn:{packager.lower()}:risk:framework:ccm-controls-v4'])
ws.append(['framework_ref_id', 'CCM-Controls-v4'])
ws.append(['framework_name', 'CCM Controls v4'])
ws.append(['framework_description', 'CCM Controls v4'])
ws.append(['tab', 'controls', 'requirements'])

ws1 = wb_output.create_sheet("controls")
ws1.append(['assessable', 'depth', 'ref_id', 'name', 'description', 'maturity'])
for row in output_table:
    ws1.append(row)
print("generate ", output_file_name)
wb_output.save(output_file_name)
