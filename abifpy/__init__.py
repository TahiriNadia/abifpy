#!/usr/bin/env python

"""Python module for reading .ab1 trace files"""

import re
import struct

# directory data structure:
# tag name, tag number, element type code, element size, number of elements
# data size, data offset, handle
FMT_DIR = '>4sIHHIIII'
# for header +file type, file version
FMT_HEAD = '>4sH4sIHHIII'
# only retrieve the data we care about:
# plate barcode, machine model, sequence, quality values sample id, well number
TAGS = {'HCFG3':'instrument', 'PBAS2':'seq', 'PCON2':'qual', 'SMPL1':'sampleid', 'TUBE1':'well'}


class Trace(object):
    """Class representing trace file"""
    def __init__(self, sfile, all_tags=False):        
        try:
            with open(sfile) as source:
                self._data = source.read()
            if not self._data[:4] == 'ABIF':
                raise IOError('Input file is not a proper .ab1 trace file')
        except IOError as (strerror):
            print "IOError: {0}".format(strerror)
        else:
            self._header = struct.unpack(FMT_HEAD, self._data[:30])
            self.version = self._header[1]
            head_elemsize = self._header[5]
            head_elemnum = self._header[6]
            head_offset = self._header[8]
            self.tags = {}
            self.id = sfile.replace('.ab1','')

            # build dictionary of tags that we care about if all_tags=False
            # otherwise get all tags
            for entry in self._gen_dir(head_offset, head_elemsize, head_elemnum):
                if not all_tags:
                    if (entry[0] + str(entry[1])) in TAGS:
                        self.tags[entry[0] + str(entry[1])] = entry
                else:
                    self.tags[entry[0] + str(entry[1])] = entry

            # retrieve attributes from tags
            for item in self.tags:
                self._decode_dir(self.tags[item])
    
    def _gen_dir(self, head_offset, head_elemsize, head_elemnum):
        """Generator for directory contents."""
        index = 0
        while index < head_elemnum:
            start = head_offset + index * head_elemsize
            finish = head_offset + (index + 1) * head_elemsize
            # added directory offset to tuple
            # to handle directories with data size <= 4 bytes
            yield struct.unpack(FMT_DIR, self._data[start:finish]) + (start,)
            index += 1

    def _decode_dir(self, 
                    (tag_name, tag_no, elem_code, elem_size, elem_no,
                     dir_size, dir_offset, dir_handle, data_offset)):
        """Extracts data from directories in the file."""
        # if data size is <= 4 bytes, data is stored inside the directory
        # so offset needs to be changed
        if dir_size <= 4:
            dir_offset = data_offset + 20

        if elem_code == 2:
            fmt = str(dir_size) + 's'
            data = struct.unpack(fmt, 
                    self._data[dir_offset:dir_offset+dir_size])[0]
            if tag_name == 'PCON':
                self.qual = self._get_qual(data)
            elif tag_name == 'PBAS':
                # replaces semi-ambiguous DNA characters with 'N'
                self.seq = re.sub("K|Y|W|M|R|S",'N',data)
       
        elif elem_code == 18:
            fmt = str(dir_size-1) + 's'
            data = struct.unpack(fmt,
                    self._data[dir_offset+1:dir_offset+dir_size])[0]
            if tag_name == 'SMPL':
                self.sampleid = data
            elif tag_name == 'TUBE':
                self.well = data
       
        elif elem_code == 19:
            fmt = str(dir_size-1) + 's'
            data = struct.unpack(fmt,
                    self._data[dir_offset:dir_offset+dir_size-1])[0]
            if tag_name == 'HCFG':
                self.instrument = data
    
    def _get_qual(self, qual):
        """Returns a list of read quality values."""
        qual_list = []
        for i in qual:
            qual_list.append(ord(i))
        return qual_list

    def seqrecord(self):
        """Returns a SeqRecord object of the trace file."""
        try:
            from Bio.Seq import Seq
            from Bio.SeqRecord import SeqRecord
            BIOPYTHON = True
        except ImportError:
            BIOPYTHON = False

        if BIOPYTHON:
            return SeqRecord(Seq(self.seq), id=self.id, name="",
                      description=self.sampleid)
        else:
            print 'Biopython was not detected. No SeqRecord was created.'
            return None

    def write(self, output=""):
        """Writes the trace file sequence to a fasta file.
        
        Keyword argument:
        output -- output file name (detault 'tracefile'.fa)

        """
        record = self.seqrecord()

        if output == "":
            output = self.id + '.fa'

        with open(output, 'rw') as tfile:
            contents = '>{0} {1}\n{2}\n'.format(
                        self.id, self.sampleid, self.seq)
            tfile.writelines(contents)

    def trim(self):
        """Trims the sequence based on quality values."""
        pass
