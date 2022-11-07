#!/usr/bin/env python3

# generate JSON with all filenames and checksum of their content
#   that is supposed to happen on each backup invocation
#   once the JSON (including checksums) has been created
#   compare the current JSON to the JSON to the last 'full backups' JSON
#     (which could be regularly done, once a month)
#   



import hashlib
import os
import json

def produce_checksum_for_file(path_to_file):
    """ Takes a file name to read out a file and returns it's md5 checksum """

    chksum = hashlib.md5() # or sha256() at your leisure
    BYTES_TO_READ_PER_ITERATION = 4_000_000
    cur_bytes_read = 0

    try:
        TOTAL_FILE_SIZE = os.path.getsize(path_to_file)
        with open(path_to_file, 'rb') as fd:

            # iterate over the file until we got it all read
            while cur_bytes_read < TOTAL_FILE_SIZE:
                curbuf = fd.read(BYTES_TO_READ_PER_ITERATION)
                cur_bytes_read += len(curbuf)
                chksum.update(curbuf)
    except:
        # in case of file read errors, a 'broken' or maybe
        #   even incorrect checksum will be calculated
        #   which is fine also. Especially in the case of empty files
        #   as it is consistent.
        pass

    return chksum.hexdigest()


def recurse_over_all_filesystem_subentries_entry(path_to_directory):

    root_node_arr = None
    dir_list         = query_dir_list(path_to_directory)

    if dir_list is not None:
        root_node_arr    = {
            'name': '.',
            'type': 'directory',
            'childNodes': [],
            'combined_checksum': ''
        }
        root_level_count = len(dir_list)
        
        for root_level_index in range(0, root_level_count):
            cur_name = dir_list[root_level_index]
            cur_path = path_to_directory + "/" + cur_name
            if os.path.exists(cur_path):
                root_node_arr['childNodes'].append(recurse_over_all_filesystem_subentries_reentrant(cur_path, cur_name))

    else:
        print("ERROR: backup-root directory could not be listed. Couldn't find anything.")
        return ""

    #TODO: generate checksums of directories
    # recurse over node structure
    recurse_over_nodes_combine_checksums(root_node_arr)
    
    return root_node_arr


def recurse_over_nodes_combine_checksums(my_node):
    if 'directory' == my_node['type']:
        # loop over all the entries
        chksum = hashlib.md5() # or sha256() at your leisure
        for index in range(0, len(my_node['childNodes'])):
            cur_node = my_node['childNodes'][index]
            if 'file' == cur_node['type']:
                chksum.update(cur_node['content_checksum'].encode('ascii'))
            elif 'directory' == cur_node['type']:
                chksum.update(recurse_over_nodes_combine_checksums(cur_node).encode('ascii'))
        my_node['combined_checksum'] = chksum.hexdigest()
        return my_node['combined_checksum']

    elif 'file' == my_node['type']: # just in case..
        return my_node['content_checksum']

    return ''
    

def recurse_over_all_filesystem_subentries_reentrant(my_root_path, my_name):
    my_node = None

    if os.path.isfile(my_root_path):
        my_node = {
            'name': my_name,
            'type': 'file',
            'content_checksum': produce_checksum_for_file(my_root_path)
        }
    elif os.path.isdir(my_root_path):
        my_node = {
            'name': my_name,
            'type': 'directory',
            'childNodes': [],
            'combined_checksum': ''
        }

        # run through all the directories' entries
        dir_list = query_dir_list(my_root_path)
        for cur_index in range(0, len(dir_list)):
            cur_name = dir_list[cur_index]
            cur_path = my_root_path + "/" + cur_name
            if os.path.exists(cur_path):
                my_node['childNodes'].append(recurse_over_all_filesystem_subentries_reentrant(cur_path, cur_name))
    else:
        print("{} does not exist".format(my_root_path))

    return my_node




def iterate_over_all_filesystem_subentries(path_to_directory):
    """ TODO: Describe """

    root_arr       = []

    cur_iter_depth = 0
    dir_list_arr   = []
    index_arr      = []
    count_arr      = []
    path_part_arr  = []

    path_part_arr.append(path_to_directory)

    dir_list_arr.append(query_dir_list(path_to_directory))
    if dir_list_arr[cur_iter_depth] is not None:
        root_arr = {
            'name': '.',
            'type': 'directory',
            'childNodes': [],
            'combined_checksum': None # TODO: need to do some backroll, after all the files have had their checksums calculated
# TODO: for being able to verbosely output the current files being checksummed, we should additionally be logging, which file we are currently accessing/running the checksum algorithm for, for big files (e.g. 1 GB, a progress meter would be nice too, but that would get to fancy (read: we don't do an in-file-progress meter, as that would probably require us, to be using threads))
        }
        count_arr.append(len(dir_list))
        index_arr.append(0)

        while 0 <= cur_iter_depth \
          and dir_list_arr[cur_iter_depth] is not None:

            if index_arr[cur_iter_depth] < count_arr[cur_iter_depth]:
                cur_name      = dir_list_arr[cur_iter_depth][index_arr[cur_iter_depth]]
                cur_file_path = build_file_path(path_part_arr, cur_iter_depth + 1, cur_name )
                if os.path.exists(cur_file_path):
                    if os.path.isfile(cur_file_path):
                         # TODO: correct this, need to address the right node..
                         root_arr[cur_iter_depth]['childNodes'].append({
                             'name': cur_name,
                             'type': 'file',
                             'content_checksum': produce_checksum_for_file(cur_file_path)
                         })
    
                         # go for the next iteration
                         index_arr[cur_iter_depth] += 1
    
                    elif os.path.isdir(cur_file_path):
                         # TODO: correct this, need to address the right node..
                         root_arr[cur_iter_depth]['childNodes'].append({
                             'name': cur_name,
                             'type': 'directory',
                             'childNodes': [],
                             'combined_checksum': None # will be calculated afterwards
                         })
    
                         # now we need to descend futher:
                         cur_iter_depth += 1
    
                         # do initialize going deeper, especially initialize index and count arrays...
                         if len(dir_list_arr) <= cur_iter_depth:
                             dir_list_arr.append([])
                             index_arr.append(0)
                             count_arr.append(0)
                             path_part_arr.append("(uninitialized)")
    
                         dir_list_arr  [cur_iter_depth] = query_dir_list(path_to_directory)
                         index_arr     [cur_iter_depth] = 0
                         count_arr     [cur_iter_depth] = len(dir_list_arr[cur_iter_depth])
                         parth_part_arr[cur_iter_depth] = cur_name

            # does the next element exist? - if no, we need to go back up,
            #   going back up and incrementing the index might occur multiple times
            #   so we need another loop here
            while index_arr[cur_iter_depth] >= count_arr[cur_iter_depth]:
                cur_iter_depth -= 1
                if 0 <= cur_iter_depth:
                    index_arr[cur_iter_depth] += 1
                else:
                    # hard break, we are done with scanning
                    # cur_iter_depth is below zero (= -1)
                    pass

    # TODO: generate checksums for directories
    # TODO: convert to JSON
    # TODO: return the JSON
    print(root_arr)

    


def build_file_path(dirs_arr, depth_of_dirs, last_path_part):
    path_str = root_path

    for i in range(0, depth_of_dirs):
        path_str = path_str + "/" + dirs_arr[i]

    path_str = path_str + "/" + last_path_part

    return path_str
    
        
        
    
    

# TODO: code
#    if dir_list is not None:
#        for cur_entry in dir_list:

# TODO: cast the resulting array to JSON and return it
            
def query_dir_list(path_to_directory):
    dir_list = None

    try:
        dir_list = os.listdir(path_to_directory)
    except:
        pass

    return dir_list
    
    

print(recurse_over_all_filesystem_subentries_entry('/home/zocken/tmp/goethe'))

        

