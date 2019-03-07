# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 16:04:01 2018

@author: bec
"""
import os 

main_dir = os.path.dirname(os.path.abspath(__file__))

def get_path(name):
    
    paths = {'inkscape':    r"C:\Program Files\Inkscape\inkscape.exe",
             'sheet1_svg':  os.path.join(main_dir,'svg\sheet_1.svg'),
             'sheet2_svg':  os.path.join(main_dir,'svg\sheet_2.svg'),
             'sheet3_1_svg':  os.path.join(main_dir,'svg\sheet_3_part1.svg'),
             'sheet3_2_svg':  os.path.join(main_dir,'svg\sheet_3_part2.svg'),
             'sheet4_1_svg':  os.path.join(main_dir,'svg\sheet_4_part1.svg'),
             'sheet4_2_svg':  os.path.join(main_dir,'svg\sheet_4_part2.svg'),
             'sheet6_svg':    os.path.join(main_dir,'svg\sheet_6.svg'),
             'sheet5_svg':    os.path.join(main_dir,'svg\sheet_5.svg'),
             'sheet7m_svg':  os.path.join(main_dir,'svg\\sheet7_month.svg'),
             'sheet7y_svg':  os.path.join(main_dir,'svg\sheet7_yearly.svg'),
             'gdalwarp':      r"C:\Program Files\QGIS 2.18\bin\gdalwarp.exe"
             }
    
    return paths[name]

