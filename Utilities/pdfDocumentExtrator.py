import fitz
import os

# PARM_PDF_IN_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage0SourcePDFFiles/Marathon OIL')
# PARM_PDF_OUT_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/Marathon OIL')

PARM_PDF_IN_FOLDER_BP = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage0SourcePDFFiles/Antero Resources')
PARM_PDF_OUT_FOLDER_BP = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/2022')


class pdfDocumentExtractor:

	def __init__(self) -> None:
		pass

	def convert_pdf_files_to_text(self, input_folder:str,out_put_folder:str):
		file_list = sorted(os.listdir(input_folder))
		#Create output directory if it does not exist
		if not os.path.exists(out_put_folder):
			os.makedirs(out_put_folder)

		for file in file_list:
			if (file =='.DS_Store'):
				pass
			else:
				inputpath = f'{input_folder}/{file}'
				outputpath = f'{out_put_folder}/{file.replace(".pdf",".txt")}'

				doc = fitz.open(inputpath) # open a document
				out = open(outputpath, "wb") # create a text output
				for page in doc: # iterate the document pages
					text = page.get_text().encode("utf8") # get plain text (is in UTF-8)
					out.write(text) # write text of page
					out.write(bytes((12,))) # write page delimiter (form feed 0x0C)
				out.close()

pdf_text_converter = pdfDocumentExtractor()

pdf_text_converter.convert_pdf_files_to_text(PARM_PDF_IN_FOLDER_BP, PARM_PDF_OUT_FOLDER_BP)