import fitz
import os

# PARM_PDF_IN_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage0SourcePDFFiles/Marathon OIL')
# PARM_PDF_OUT_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/Marathon OIL')
PARM_BGNYEAR = 2013  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 2013 # User selected end period.

PARM_PDF_IN_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage0SourcePDFFiles')
PARM_PDF_OUT_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles')
PARM_ARCHIVE_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/ProcessedPdfFiles')


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
				## Archive processed file
				processed_path_folder = f'{PARM_ARCHIVE_FOLDER}'
				if not os.path.exists(processed_path_folder):
					os.makedirs(processed_path_folder)
		
				processed_path = f'{processed_path_folder}/{file}'
				os.rename(inputpath,processed_path)
				print("Successfully created the text file from pdf file:")
				print("                    Source:"+inputpath)
				print("                    Target: "+outputpath)



pdf_text_converter = pdfDocumentExtractor()

for year in range(PARM_BGNYEAR, PARM_ENDYEAR+1):
	input_path = f'{PARM_PDF_IN_FOLDER}/{year}'
	ouput_path =  f'{PARM_PDF_OUT_FOLDER}/{year}'
	pdf_text_converter.convert_pdf_files_to_text(input_path, ouput_path)