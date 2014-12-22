#!/usr/bin/env python
from py_w3c.validators.html.validator import HTMLValidator
from pprint import pprint
import csv
import collections
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
import sys
import os
import time
import argparse



parser = argparse.ArgumentParser(description='analyzes the wave and w3c APIs and ingests responses into Solr')
parser.add_argument('-f','--file', help='required-name of csv file', type=str)
parser.add_argument('-c','--core', help='--required-name of Solr core', required=True, type=str)
parser.add_argument('-u','--username', help='--optional-username for Solr user', type=str)
parser.add_argument('-p','--password', help='--optional-password for Solr user', type=str)
parser.add_argument('-d','--directory', help='--optional-specify name of overarching directory for your data', type=str)
args = vars(parser.parse_args())

csv_file = args['file']
core = args['core']
username = args['username']
password = args['password']
directory = args['directory']

# FUNCTIONS
def convert(input):
	if isinstance(input, dict):
		return {convert(key): convert(value) for key, value in input.iteritems()}
	elif isinstance(input, list):
		return [convert(element) for element in input]
	elif isinstance(input, unicode):
		return input.encode('utf-8')
	else:
		return input

def flatten(d, parent_key='', sep='_'):
	items = []
	for k, v in d.items():
		new_key = parent_key + sep + k if parent_key else k
		if isinstance(v, collections.MutableMapping):
			items.extend(flatten(v, new_key).items())
		else:
			items.append((new_key, v))
	return dict(items)

def solrize_w3c(input, we):
	dictionary = {}
	each_id = [(each.get('message')) for each in input]
	count = collections.Counter(each_id)
	if isinstance(input, list):
		for each_dict in input:
			if each_dict.get('explanation') == None:
				each_dict['explanation'] = "None"
				# below might not work
			id = each_dict['message'].replace('"', "").replace(" ", "_").replace(":", "_").replace(".", "")
			dictionary.update({id: {we+"_count": count[each_dict['message']], we+"_message": each_dict['message'], we+"_explanation": each_dict['explanation'], }})
	return {we: {"total_count": len(input), "categories":dictionary}}

def save(name, data_type, url, output_directory, subdirectory):
	print "Saving "+data_type+" for "+url+" at ./"+output_directory+"/"+subdirectory
	file_name = output_directory+'/'+subdirectory+'/'+url+'_'+data_type+'.json'
	f = open(file_name, 'w')
	f.write(json.dumps(name))
	f.close()

if directory is None:
	now = datetime.datetime.now()
	newDirName = now.strftime("%Y_%m_%d")
	print "Making directory " + newDirName
	if not os.path.isdir(newDirName):
		os.mkdir(newDirName)
		directory = newDirName
	else:
		print "This directory already exists. You could possibly overwrite your data if you continue."
		exit()

# CSV
csv_data = []
with open(csv_file, 'rU') as f:
	reader = csv.reader(f)
	csv_hash = {rows[0]:rows[1] for rows in reader}
	for lib_name, url in csv_hash.items():
		try:
			url = url.replace(" ", "")
			lib_name = lib_name.replace(" ", "_")
			# Create folder for your current library's data
			print "Creating folder for "+lib_name
			subdirectory = lib_name
			dir_path = "./"+directory+"/"+subdirectory
			if not os.path.exists(dir_path):
				os.makedirs(dir_path)


			# W3C Query/Response
			vld = HTMLValidator()
			vld.validate(url)
			w3c_warnings = convert(vld.warnings)
			save(w3c_warnings, 'w3c_warnings', lib_name, directory, subdirectory)

			w3c_errors = convert(vld.errors)
			save(w3c_errors, 'w3c_errors', lib_name, directory, subdirectory)

			w3c_warnings = solrize_w3c(w3c_warnings, "w3c_warnings")
			w3c_errors = solrize_w3c(w3c_errors, "w3c_errors")
			w3c = dict(w3c_warnings, **w3c_errors)

			w3c = flatten(w3c)


			time.sleep(1)

			print "Querying Wave API for data about "+url
			wave = requests.get("http://wave.webaim.org/api/request?key=ndb38wCF181&url="+url+"&reporttype=2")
			wave = wave.json()
			save(wave, 'wave', lib_name, directory, subdirectory)
			wave = flatten(convert(wave))

			solr_data = [dict(w3c, **wave)]
			save(solr_data, 'solr_ingest', lib_name, directory, subdirectory)
			solr_data = json.dumps(solr_data)


			# 	push to solr
			print "Pushing to Solr"
			headers = {'content-type' : 'application/json'}
			url = 'http://localhost:8983/solr/'+core+'/update?commit=true'
			if username is None and password is None:
				auth = ''
			else:
				auth = HTTPBasicAuth(username, password)

			r = requests.post(url, auth=auth, data=solr_data, headers=headers)
			print r.text
		except Exception, e:
			# Catch all the errors that might stop the script, append them to an error file, and then move onto the next url
			print e.__doc__
			print e.message
			myfile = open("errors.txt", "a")
			myfile.write(lib_name)
			myfile.write(e.message)
			myfile.close()
			continue