################################################################################
#
#  Copyright 2014-2016 Eric Lacombe <eric.lacombe@security-labs.org>
#
################################################################################
#
#  This file is part of fuddly.
#
#  fuddly is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  fuddly is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with fuddly. If not, see <http://www.gnu.org/licenses/>
#
################################################################################

from framework.data_model import *
from framework.global_resources import *
from framework.value_types import *


class PNG_DataModel(DataModel):

    file_extension = 'png'
    name = 'png'

    def create_node_from_raw_data(self, data, idx, filename):
        nm = 'PNG_{:0>2d}'.format(idx)
        png = self.png.get_clone(nm, new_env=True)
        status, off, size, name = png.absorb(data, constraints=AbsNoCsts(size=True))

        print('{:s} Absorb Status: {!r}, {:d}, {:d}, {:s}'.format(nm, status, off, size, name))
        print(' \_ length of original png: {:d}'.format(len(data)))
        print(' \_ remaining: {!r}'.format(data[size:size+1000]))

        if status == AbsorbStatus.FullyAbsorbed:
            print("--> Create {:s} from provided PNG samples.".format(nm))
            return png
        else:
            return Node(nm, values=['PNG ABSORBSION FAILED'])


    def build_data_model(self):

        png_simple_desc = \
        {'name': 'PNG_model',
         'contents': [
             {'name': 'sig',
              'contents': String(values=[u'\x89PNG\r\n\x1a\n'], size=8)},
             {'name': 'chunks',
              'qty': (2,200),
              'contents': [
                   {'name': 'len',
                    'contents': UINT32_be()},
                   {'name': 'type',
                    'contents': String(values=['IHDR', 'IEND', 'IDAT', 'PLTE'], size=4)},
                   {'name': 'data_gen',
                    'contents': lambda x: Node('data', value_type=String(size=x[0].cc.get_raw_value())),
                    'node_args': ['len']},
                   {'name': 'crc32_gen',
                    'contents': CRC(vt=UINT32_be, clear_attrs=[MH.Attr.Mutable]),
                    'node_args': ['type', 'data_gen']}
              ]}
         ]}

        png_desc = \
        {'name': 'PNG_model',
         'contents': [
             {'name': 'sig',
              'contents': String(values=[u'\x89PNG\r\n\x1a\n'], size=8)},
             {'name': 'chunks',
              'qty': (2,200),
              'contents': [
                  {'name': 'len',
                   'contents': UINT32_be()},
                  {'name': 'chk',
                   'contents': [
                       {'weight': 10,
                        'contents': [
                            {'name': 'type1',
                             'contents': String(values=['IHDR'], size=4),
                             'absorb_csts': AbsFullCsts()},
                            {'name': 'width',
                             'contents': UINT32_be()},
                            {'name': 'height',
                             'contents': UINT32_be()},
                            {'name': 'bit_depth',
                             'contents': UINT8(values=[1,2,4,8,16])},
                            {'name': 'color_type',
                             'contents': UINT8(values=[0,2,3,4,6])},
                            {'name': 'compression_method',
                             'contents': UINT8(values=[0])},
                            {'name': 'filter_method',
                             'contents': UINT8(values=[0])},
                            {'name': 'interlace_method',
                             'contents': UINT8(values=[0,1])}
                        ]},
                       {'weight': 5,
                        'contents': [
                            {'name': 'type2',
                             'contents': String(values=['IEND', 'IDAT', 'PLTE'], size=4)},
                            {'name': 'data_gen',
                             'contents': lambda x: Node('data', value_type=String(size=x.get_raw_value())),
                             'node_args': 'len'}
                        ]}
                   ]},
                  {'name': 'crc32_gen',
                   'contents': CRC(vt=UINT32_be, clear_attrs=[MH.Attr.Mutable]),
                   'node_args': ['chk']}
              ]}
         ]}


        mb = NodeBuilder()
        self.png = mb.create_graph_from_desc(png_desc)

        self.png_dict = self.import_file_contents(extension='png')
       
        self.register(*self.png_dict.values())


data_model = PNG_DataModel()

