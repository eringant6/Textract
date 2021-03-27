import webbrowser, os
import json
import boto3
import io
from io import BytesIO
import sys
from pprint import pprint
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import tempfile


def pdf_to_png(file_path):
    images = convert_from_path(file_path)
    bytes_list = []
    for image in images:
        imgByteArr = io.BytesIO()
        image.save(imgByteArr, format='png')
        imgByteArr = imgByteArr.getvalue()
        bytes_list.append(imgByteArr)
    return bytes_list
        
def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        # create new row
                        rows[row_index] = {}
                        
                    # get the text value
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] =='SELECTED':
                            text +=  'X '    
    return text


def get_table_csv_results(file_name):

    img_test = pdf_to_png(file_name)
 
    print('Image loaded', file_name)
    
    csv_list = []
    for image in img_test:
        # process using image bytes
        # get the results     
        bytes_test = bytearray(image)
        client = boto3.client('textract') 
        response = client.analyze_document(Document={'Bytes': image}, FeatureTypes=['TABLES'])

        # Get the text blocks
        blocks=response['Blocks']
        #pprint(blocks)

        blocks_map = {}
        table_blocks = []
        for block in blocks:
            blocks_map[block['Id']] = block
            if block['BlockType'] == "TABLE":
                table_blocks.append(block)

        if len(table_blocks) <= 0:
            return "<b> NO Table FOUND </b>"

        csv = ''
        for index, table in enumerate(table_blocks):
            csv += generate_table_csv(table, blocks_map, index +1)
            csv += '\n\n'
        csv_list.append(csv)
    return csv_list

def generate_table_csv(table_result, blocks_map, table_index):
    rows = get_rows_columns_map(table_result, blocks_map)

    table_id = 'Table_' + str(table_index)
    
    # get cells.
    csv = 'Table: {0}\n\n'.format(table_id)

    for row_index, cols in rows.items():
        
        for col_index, text in cols.items():
            csv += '{}'.format(text) + ","
        csv += '\n'
        
    csv += '\n\n\n'
    return csv

def main(file_name):
    table_csv = get_table_csv_results(file_name)
    index = 0
    for csv in table_csv:
        
        output_file = f'output{index}.csv'
        index += 1
        # replace content
        with open(output_file, "wt") as fout:
            fout.write(csv)

    # show the results
    print('CSV OUTPUT FILE: ', output_file)


if __name__ == "__main__":
    file_name = sys.argv[1]
    main(file_name)
