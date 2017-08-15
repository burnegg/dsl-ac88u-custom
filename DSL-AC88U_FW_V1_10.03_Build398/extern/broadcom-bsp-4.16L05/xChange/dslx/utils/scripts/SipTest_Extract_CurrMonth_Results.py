import sys
import os
import re
import string
import time
from datetime import date

# The location of the result files generated by Abacus
target_dir = 'C:\Abacus 3.24\RESULTS\\'

# The filename of the result file generated by Abacus
target_filename = '\\Rep_0001.sts'

# The location of the html output file
output_dir = 'C:\Abacus 3.24\RESULTS\RESULTS_HTML\\'

def open_result_file(path):
	'''
	Purpose
		Open the file at the given path.
		If the file cannot be opened or is missing
			print error message and return None.
		else
			return the file object.
	Precondition
		path is a valid string
	'''
	# if a path is given
	if path:
		try:
			f = open(path, 'r')
		except IOError:
			# get here if path is None, file not found or cannot be opened
			return None
		else:
			return f	


def get_section(f, section, next_section):
	'''
	Purpose
		Return an array of lines containing the section
		  matched starting with section until next_section
		If not matched, return None

	Precondition
		f is a valid file object for reading
		section and next_section are a valid string
	'''

	if section and f:
		line_ind = 0
		content = f.readlines()
		f.close()

		start = 0
		# search for the section's first line index
		for line in content:
			m = re.search('^'+section,line)
			if m:
				start = line_ind
				break
			line_ind += 1

		# cannot find the section
		if start == len(content)-1:
			return None
	
		# find the line index before the next section
		# if next_section is not supplied, 
		# return the rest of the file.
		if next_section == '':
			return content[start:]
		line_ind = start+1
		end = len(content)-1
		for line in content[start+1:]:
			m = re.search('^'+next_section,line)
			if m:
				end = line_ind
				break
			line_ind += 1
		if end >= len(content)-1:
			return content[start:len(content)-1]
		
		return content[start:end]	
	else:
		return None


def get_env(filename):
	'''
	Purpose
		get the current evnironment
	Precondition
		filename is a valid string
	'''
	# retrieve the Current Enviornment
	Curr_Env = []
	f = open_result_file(filename)
	if not f:
		return None

	for line in get_section(f,'Current environment','\r\n'):
		Curr_Env.append(line)
	return Curr_Env	


def get_scripts(filename):
	'''
	Purpose
		get the Script section
	Precondition
		filename is a valid string
	'''

	# retrieve the Scripts section
	Scripts = []
	f = open_result_file(filename)
	if not f:
		return None

	for line in get_section(f,'Scripts','Test Status'):
		if line.lstrip('\r\n'):
			Scripts.append(line)

	return Scripts

def get_events(filename):
	'''
	Purpose
		get the Event section
	Precondition
		filename is a valid string
	'''
	# retrieve the Events section
	Events = []
	f = open_result_file(filename)
	if not f:
		return None

	for line in get_section(f,'Events','System Events'):
		# skip Debug message lines
		if not ('Debug message' in line or re.search('^>',line)):
			if line.lstrip('\r\n'):
				Events.append(line)
	return Events

def process_scripts(scripts):
	'''
	Purpose
		Retrive infomation about test steps.
		Returns the a list of dictionries, in which test step script name,
		starting line num, and ending line num are included.

	Precondition
		scripts is a valid list
	'''
	if scripts:
		# find the starting index of each test step scripts in the list
		start_pos = []
		for ind in range(len(scripts)):
			# find the script name
			m = re.search('^     ',scripts[ind])
			if m:
				start_pos.append(ind)	
	else:
		return None

	# get the script name and its start and end indices
	groups = []
	for i in range(len(start_pos)):
		script_name = scripts[start_pos[i]].strip()
		
		start = start_pos[i]
	
		if i == len(start_pos)-1:	# the last script
			end = len(scripts)-1
		else:
			end = start_pos[i+1]-1

		groups.append( {'script_name':script_name, \
				'start': start, \
				'end': end} )

	# adjust the script line num according to the index in the list
	for i in range(len(groups)):
		groups[i]['start_act'] = groups[i]['start']-1-i
		groups[i]['end_act'] = groups[i]['end']-2-i
	return groups

def gen_currmonth_dirs(target_dir, currmonth_str):
	'''
	Purpose
		Walk the directory tree start from target_dir and 
		genereate a list of directories with the prefix currmonth_str.
		Return a list of dictionaries. The dictionary keys are the distinct
		dates, and the values are lists of directories.
	Precondition
		target_dir and currmonth_str are valid strings
	'''
	# walk the directory tree and find the result directories
        dirs = os.walk(target_dir)
        for r, d, f in dirs:
                if r == target_dir:
                        result_dirs = d 

	# get the dirctories of the current month
        groups = []
        for d in result_dirs:
		# match for the directories with prefix currmonth_str
                m = re.search('^'+currmonth_str+'(\d\d)',d)
                if m:
			# distinct dates
                        if currmonth_str+m.group(1) not in groups:
                                groups.append(currmonth_str+m.group(1))

	# group the directories by dates
	results = {}
	for group_prefix in groups:
		group = []
		for d in result_dirs:
			m = re.search('^'+group_prefix,d)
			if m:
				group.append(d)
		group.sort()
		results[group_prefix] = group
	return results
	

def process_result_file(path):
	'''
	Purpose
		Extract the desired sections from a result file at the given path.
		If path is valid path to a valid result file
			returns a 2-tuple (number of failures, contents).
		or
			returns a 2-tuple (0, None)
	Precondition
		path is a valid string
		
	'''
	# retrieve the Current Enviornment
	Curr_Env = get_env(path)
	if not Curr_Env:
		return 0, None
		
	# retrieve the Scripts section
	Scripts = get_scripts(path)
	if not Scripts:
		return 0, None
	Scripts_info = process_scripts(Scripts)

	# retrieve the Events section
	Events = get_events(path)
	if not Events:
		return 0, None
	
	# find out the Act colum indices
	start, end = Events[1].find('Act'), Events[1].find('Event')

	# store the result to a list of lines
	result = []
	
	# Current Enviornment
	result.append(Curr_Env[0])
	result.append('\r\n')

	# Events
	fail_count = 0 
	for line in Events[0:3]: 
		result.append(line)

	for e in Events[3:-1]:			# event lines
		line = e.rstrip()
		if e[start:end-1].strip():
			for s in Scripts_info:
				if e[start:end-1].strip().isdigit() and \
				    int(e[start:end-1].strip()) in range(s['start_act'],s['end_act']):
					fail_count += 1        # count the number of failures
					line += '\t ==> During '+s['script_name']
		result.append(line+'\r\n')
	result.append(Events[-1])
	result.append('\r\n')
	
	# Scripts
	for s in Scripts:
		result.append(s)

	return fail_count, result

def gen_aggregated_result(dirs, target_dir):
	'''
	Purpose
		generate an aggregated result that contains a table of tests grouped and sorted by date
		and the result containing the extracted sections from result files sorted by date.
	Precondition
		dirs is a valid dirent object and target_dir is valid string
	'''
	global target_filename
	table = {}
        final_result = {}
        for date in dirs:
                table[date] = []        
		final_result[date] = []
                for d in dirs[date]:
			print 'Processing '+target_dir+d+target_filename
                        fail_count, result = process_result_file(target_dir+d+target_filename)
                        env = None
                        if not result:
                                result = ['Result file is missing from directory '+d+'\r\n']

                        env = result[0].replace('Current environment:','').strip()
                        table[date].append([env, fail_count, d])
                        final_result[date].append([d+'_'+env,result])
	return table,final_result

def gen_html(table, final_result):
	'''
	Purpose
		Generate the final result in html format
		If table and final_result are None
			print error message and exit
		else generate the html under target_dir/RESULTS_HTML/
	Precondition
		None
	'''
	if not table or not final_result:
		print 'Invalid extracted information'
		sys.exit(-1)

	today = date.today()
	currmonth_str = today.strftime('%Y%m')

	test_dates = table.keys()
	test_dates.sort()

	test_dates_content = table.keys()
	test_dates_content.sort()

	'''
	 We have the raw aggregated results in the current month.
	 Now output to a html file.
	'''
	output_file = open(output_dir+currmonth_str+'_Results.html','w')

	print 'Generating the result html file ....'

	print >> output_file, '<html><body>'
	print >> output_file, '<h2 id="main">SIP Advanced Features Test Results</h1></br>'
	print >> output_file, 'Last update: '+time.strftime('%Y/%m/%d %H:%M:%S')+'</br>'
	print >> output_file, '<center><table border=1>'

	col = 0
	adate = test_dates.pop()
	print >> output_file, '<tr>'
	while adate:
		print '\tGenerating results from ' + adate
		if col%3 == 0:
			print >> output_file, '<tr>'	
		print >> output_file, '<td valign=top>'
		print >> output_file, '<center><b><u>'+adate+'</u></b></center><br>'
		print >> output_file, '<ul>'

		for l in table[adate]:
			line = l[0]
			count = l[1]
			dirname = l[2]
			print >> output_file, '<li>'+'<a href="#'+dirname+'_'+line+'">'+line+'</a>'
			if count > 0:
				print >> output_file, '&nbsp<img src="http://bcacpe-hudson.broadcom.com/plugin/warnings/icons/warnings-24x24.png">'+\
				    str(count)
		print >> output_file, '</ul>'
		print >> output_file, '</td>'
		col +=1
		if col%3 == 0 :
			print >> output_file, '</tr>'
		if len(test_dates) == 0:
			adate = None
		else:
			adate = test_dates.pop()
	print >> output_file, '</table></center>'
	print >> output_file, '<hr>'

	adate = test_dates_content.pop()
	while adate:
		for lines in final_result[adate]:
			anchor = lines[0]
			print >> output_file, '<h3 id="'+anchor+'">'+anchor+'</h2><br><a href="#main">back to top</a><br>'
			print >> output_file, '<pre>'
			for line in lines[1]:
				print >> output_file, line,
			print >> output_file, '</pre>'
			print >> output_file, '<hr>'	

		if len(test_dates_content) == 0:
			adate = None
		else:
			adate = test_dates_content.pop()

def main():
	global target_dir

	# get the timestamp of the current month
        today = date.today()
        currmonth_str = today.strftime('%Y%m')

	# get the result directories of the current month
	dirs = gen_currmonth_dirs(target_dir, currmonth_str)

	# extract the results from the result directories of the current month
	table, final_result = gen_aggregated_result(dirs, target_dir)

	# generate the test result summary html file from the results extracted
	gen_html(table, final_result)

if __name__ == '__main__':
	# invoke main function
	# pass the command line arguments excluding the script name
	sys.exit(main())