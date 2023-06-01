mkdir IndexDownloads1
cp Indexdownloads/*.txt IndexDownloads1
rm -d -R Indexdownloads
mv IndexDownloads1 IndexDownloads


case 'LINESEP>ITEM1':print(tag_name)
case 'LINESEP>ITEM1A':print(tag_name)
case 'LINESEP>ITEM1B':print(tag_name)
case 'LINESEP>ITEM2':print(tag_name)
case 'LINESEP>ITEM3':print(tag_name)
case 'LINESEP>ITEM4':print(tag_name)
case 'LINESEP>ITEM5':print(tag_name)
case 'LINESEP>ITEM6':print(tag_name)
case 'LINESEP>ITEM7':print(tag_name)
case 'LINESEP>ITEM7A':print(tag_name)
case 'LINESEP>ITEM8':print(tag_name)
case 'LINESEP>ITEM9':print(tag_name)
case 'LINESEP>ITEM9A':print(tag_name)
case 'LINESEP>ITEM9B':print(tag_name)
case 'LINESEP>ITEM9C':print(tag_name)
case 'LINESEP>ITEM10':print(tag_name)
case 'LINESEP>ITEM11':print(tag_name)
case 'LINESEP>ITEM12':print(tag_name)
case 'LINESEP>ITEM13':print(tag_name)
case 'LINESEP>ITEM14':print(tag_name)
case 'LINESEP>ITEM15':print(tag_name)
case 'LINESEP>ITEM16':print(tag_name)


N'{conformedName}'

        N'{self.conformed_name}', N'{self.standard_industry_classification}', N'{self.irs_number}' ,N'{self.state_of_incorporation}',\
        N'{self.fiscal_year_end}', N'{self.form_type}', N'{self.street_1}',N'{self.city}', N'{self.state}',N'{self.zip}',N'{self.form_item1}',\
        N'{self.form_item1A}', N'{self.form_item1B}',N'{self.form_item2}',N'{self.form_item3}',N'{self.form_item4}',N'{self.form_item5}',\
        N'{self.form_item6}',N'{self.form_item7}',N'{self.form_item7A}', N'{self.form_item8}', N'{self.form_item9}',N'{self.form_item9A}',\
        N'{self.form_item9B}',N'{self.form_item9C}',N'{self.form_item10}',N'{self.form_item11}',N'{self.form_item12}',N'{self.form_item13}',\
        N'{self.form_item14}',N'{self.form_item15}',N'{self.form_item16}'



        try:
           
            return 1
        except (Exception) as exc:

            print(f'Error Processing File: = {self.f_input_file_path}\n')
            if self.f_failed_log:
                f_log = open(self.f_failed_log, 'a')
                f_log.write(f'{dt.datetime.now()}\n' +
                            f'Error Processing File: {self.f_input_file_path}\n')
                f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
                f_log.flush()
            return 0