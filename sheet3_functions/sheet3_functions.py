# -*- coding: utf-8 -*-
"""
Created on Tue Nov 15 14:21:43 2016

@author: bec
"""
import os
import csv
import datetime
import numpy as np
import calendar
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.lines as mlines
import matplotlib.patches as mpatches


import WA_Hyperloop.becgis as becgis
import WA_Hyperloop.get_dictionaries as gd
from WA_Hyperloop.paths import get_path

def create_sheet3(complete_data, metadata, output_dir):
    
    output_dir = os.path.join(output_dir, metadata['name'], 'sheet3')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    HIWC_dict = gd.get_hi_and_ec()
    wp_y_irrigated_dictionary, wp_y_rainfed_dictionary, wp_y_non_crop_dictionary = gd.get_sheet3_empties()
    years = dict()

    LULC = becgis.OpenAsArray(metadata['lu'], nan_values = True)
    
    for crop in metadata['crops']:
        if crop[4] in LULC:
            start_dates, end_dates = import_growing_seasons(crop[0])
            result_seasonly = calc_Y_WP_seasons(start_dates, end_dates, metadata['lu'], crop[4], crop[1], complete_data['etg'][0], complete_data['etg'][1], complete_data['etb'][0], complete_data['etb'][1], complete_data['ndm'][0], complete_data['ndm'][1], complete_data['p'][0], complete_data['p'][1], os.path.join(output_dir, 'WP_Y_Seasonly_csvs'), HIWC_dict, ab = (1.0,0.9))
            result = calc_Y_WP_year(result_seasonly, os.path.join(output_dir, 'WP_Y_Yearly_csvs'), crop[1])
            plot_Y_WP(result, os.path.join(output_dir,'WP_Y_Yearly_graphs'), croptype = crop[1], catchment_name = metadata['name'], filetype = 'png')
            plot_Y_WP(result_seasonly, os.path.join(output_dir,'WP_Y_Seasonly_graphs'), croptype = crop[1], catchment_name = metadata['name'], filetype = 'png')
            if crop[4] > 50:
                wp_y_irrigated_dictionary[crop[2]][crop[3]] = result
            else:
                wp_y_rainfed_dictionary[crop[2]][crop[3]] = result
            years[crop[4]] = [date.year for date in read_csv(result)[0]][1:]
        else:  #multiple-crop class          
#            print "skipping crop with lu-class {0}, not on LU-map".format(crop[4])            
            cropmask_fh=crop[4]
            crop=int(os.path.split(cropmask_fh)[-1].split('.')[0])
            start_dates, end_dates = import_growing_seasons(crop[0])
            WP_Y_Yearly_csvs_list=[]
            for subcrop in crop[1]:            
                result_seasonly = calc_Y_WP_seasons(start_dates, end_dates, cropmask_fh, subcrop, crop[1][subcrop], complete_data['etg'][0], complete_data['etg'][1], complete_data['etb'][0], complete_data['etb'][1], complete_data['ndm'][0], complete_data['ndm'][1], complete_data['p'][0], complete_data['p'][1], os.path.join(output_dir, 'WP_Y_Seasonly_csvs'), HIWC_dict, ab = (1.0,0.9))
                result = calc_Y_WP_year(result_seasonly, os.path.join(output_dir, 'WP_Y_Yearly_csvs'), crop[1][subcrop]) 
                plot_Y_WP(result, os.path.join(output_dir,'WP_Y_Yearly_graphs'), croptype = crop[1][subcrop], catchment_name = metadata['name'], filetype = 'png')
                plot_Y_WP(result_seasonly, os.path.join(output_dir,'WP_Y_Seasonly_graphs'), croptype = crop[1][subcrop], catchment_name = metadata['name'], filetype = 'png')
                WP_Y_Yearly_csvs_list.append(result)
            #saverage yield and sum consumption of all subcrops
            finalresult= summarize_subcrops(WP_Y_Yearly_csvs_list,os.path.join(output_dir, 'WP_Y_Yearly_csvs'),crop)
            if crop>50:
                wp_y_irrigated_dictionary[crop[2]][crop[3]] = finalresult
            else:
                wp_y_rainfed_dictionary[crop[2]][crop[3]] = finalresult
            years[crop[4]] = [date.year for date in read_csv(result)[0]][1:]
            continue
    
    if metadata['non_crop'] is not None:
        for i, non_crop in enumerate([metadata['non_crop']['meat'], metadata['non_crop']['milk'], metadata['non_crop']['aquaculture'], metadata['non_crop']['timber']]):
            years[i] = [date.year for date in read_csv(non_crop)[0]][1:]
            crp = ['Meat', 'Milk', 'Aquaculture', 'Timber']
            plot_Y_WP(result, os.path.join(output_dir,'WP_Y_Yearly_graphs'), croptype = crp[i], catchment_name = metadata['name'], filetype = 'png')

    years = becgis.CommonDates(years.values())
    
    if metadata['non_crop'] is not None:
        wp_y_non_crop_dictionary['Livestock']['Meat'] = metadata['non_crop']['meat']
        wp_y_non_crop_dictionary['Livestock']['Milk'] = metadata['non_crop']['milk']
        wp_y_non_crop_dictionary['Fish (Aquaculture)']['-'] = metadata['non_crop']['aquaculture']
        wp_y_non_crop_dictionary['Timber']['-'] = metadata['non_crop']['timber']

    for year in years:
        csv_fh_a, csv_fh_b = create_sheet3_csv(wp_y_irrigated_dictionary, wp_y_rainfed_dictionary, wp_y_non_crop_dictionary, year, output_dir)
        output_fh_a = csv_fh_a[:-3] + 'png'
        output_fh_b = csv_fh_b[:-3] + 'png'
        sheet3a_fh, sheet3b_fh = create_sheet3_png(metadata['name'], str(year), ['km3/year', 'kg/ha/year', 'kg/m3'], [csv_fh_a, csv_fh_b], [output_fh_a, output_fh_b], template = [get_path('sheet3_1_svg'),get_path('sheet3_2_svg')])
     
    return complete_data

def create_sheet3_csv(wp_y_irrigated_dictionary, wp_y_rainfed_dictionary, wp_y_non_crop_dictionary, year, output_dir):
    """
    Creates a csv file that can be used to create sheet3b.
    
    Parameters
    ----------
    wp_y_irrigated_dictionary : dict
        Dictionary in which the filehandles pointing to csv-files containing
        the Yield and WP values are specified, as generated by calc_Y_WP_year.
    wp_y_rainfed_dictionary : dict
        Dictionary in which the filehandles pointing to csv-files containing
        the Yield and WP values are specified, as generated by calc_Y_WP_year.
    wp_y_non_crop_dictionary : dict
        Dictionary in which the filehandles pointing to csv-files containing
        the Yield and WP values are specified. See examples.
    year : int
        Variable specifying for what year the csv needs to be generated.
    output_dir : str
        String pointing to folder to store results
        
    Returns
    -------
    output_csv_fh_b : str
        Filehandle pointing to the generated output.
        
    Examples
    --------
    >>> results_rice = r'D:\\project_ADB\\Catchments\\VGTB\\sheet3\\Yearly_Yields_WPs_Rice - Irrigated.csv'
    
    >>> wp_y_irrigated_dictionary = {
            'Cereals': {'-': result_rice},
            'Non-cereals': {'Root/tuber-crops':None, 'Leguminous-crops':None, 'Sugar-crops':None, 'Merged':None},
            'Fruit & vegetables': {'Vegetables&Melons':None, 'Fruits&Nuts':None, 'Merged':None},
            'Oilseeds': {'-': None},
            'Feed crops': {'-': None},
            'Beverage crops': {'-': None},
            'Other crops': {'-': None}}

    >>> wp_y_rainfed_dictionary = {
            'Cereals': {'-':None},
            'Non-cereals': {'Root/tuber-crops':None, 'Leguminous-crops':None, 'Sugar-crops':None, 'Merged':None},
            'Fruit & vegetables': {'Vegetables&Melons':None, 'Fruits&Nuts':None, 'Merged':None},
            'Oilseeds': {'-': None},
            'Feed crops': {'-': None},
            'Beverage crops': {'-': None},
            'Other crops': {'-': None}}

    >>> wp_y_non_crop_dictionary = {
            'Livestock': {'Meat':None, 'Milk':None},
            'Fish (Aquaculture)': {'-':None},
            'Timber': {'-':None}}
    """
    output_dir = os.path.join(output_dir, 'sheet3_yearly')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_csv_fh_b = os.path.join(output_dir, 'sheet3b_{0}.csv'.format(year))
    output_csv_fh_a = os.path.join(output_dir, 'sheet3a_{0}.csv'.format(year))
    
    first_row_b = ["USE","CLASS","SUBCLASS","TYPE","SUBTYPE","LAND_PRODUCTIVITY","WATER_PRODUCTIVITY"]
    first_row_a = ["USE","CLASS","SUBCLASS","TYPE","SUBTYPE","WATER_CONSUMPTION"]
    
    csv_file_b = open(output_csv_fh_b, 'wb')
    writer_b = csv.writer(csv_file_b, delimiter=';')
    writer_b.writerow(first_row_b)
    
    csv_file_a = open(output_csv_fh_a, 'wb')
    writer_a = csv.writer(csv_file_a, delimiter=';')
    writer_a.writerow(first_row_a)
    
    for TYPE in wp_y_irrigated_dictionary.keys():
        for SUBTYPE in wp_y_irrigated_dictionary[TYPE].keys():
            if type(wp_y_irrigated_dictionary[TYPE][SUBTYPE]) is type(None):
                writer_b.writerow(["CROP","IRRIGATED","Yield rainfall",TYPE,SUBTYPE,"nan","nan"])
                writer_b.writerow(["CROP","IRRIGATED","Incremental yield",TYPE,SUBTYPE,"nan","nan"])
                writer_b.writerow(["CROP","IRRIGATED","Total yield",TYPE,SUBTYPE,"nan","nan"])
                writer_a.writerow(["CROP","IRRIGATED","ET rainfall",TYPE,SUBTYPE,"nan"])
                writer_a.writerow(["CROP","IRRIGATED","Incremental ET",TYPE,SUBTYPE,"nan"])
            else:                
                start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WCblue, WCgreen = read_csv(wp_y_irrigated_dictionary[TYPE][SUBTYPE])
                mask = start_dates == datetime.date(year,1,1)
                writer_b.writerow(["CROP","IRRIGATED","Yield rainfall",TYPE,SUBTYPE,Ypr[mask][0],WPgreen[mask][0]])
                writer_b.writerow(["CROP","IRRIGATED","Incremental yield",TYPE,SUBTYPE,Yirr[mask][0],WPblue[mask][0]])
                writer_b.writerow(["CROP","IRRIGATED","Total yield",TYPE,SUBTYPE,Y[mask][0],WP[mask][0]])              
                writer_a.writerow(["CROP","IRRIGATED","ET rainfall",TYPE,SUBTYPE,WCgreen[mask][0]])
                writer_a.writerow(["CROP","IRRIGATED","Incremental ET",TYPE,SUBTYPE,WCblue[mask][0]])
                
    for TYPE in wp_y_rainfed_dictionary.keys():
        for SUBTYPE in wp_y_rainfed_dictionary[TYPE].keys():
            if type(wp_y_rainfed_dictionary[TYPE][SUBTYPE]) is type(None):
                writer_b.writerow(["CROP","RAINFED","Yield",TYPE,SUBTYPE,"nan","nan"])
                writer_a.writerow(["CROP","RAINFED","ET",TYPE,SUBTYPE,"nan"])
            else:
                start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WCblue, WCgreen  = read_csv(wp_y_rainfed_dictionary[TYPE][SUBTYPE])
                mask = start_dates == datetime.date(year,1,1)
                writer_b.writerow(["CROP","RAINFED","Yield",TYPE,SUBTYPE,Y[mask][0],WP[mask][0]])
                writer_a.writerow(["CROP","RAINFED","ET",TYPE,SUBTYPE,WC[mask][0]])
    
    for TYPE in wp_y_non_crop_dictionary.keys():
        for SUBTYPE in wp_y_non_crop_dictionary[TYPE].keys():
            if type(wp_y_non_crop_dictionary[TYPE][SUBTYPE]) is type(None):
                writer_b.writerow(["NON-CROP","RAINFED","Yield",TYPE,SUBTYPE,"nan","nan"])
                writer_b.writerow(["NON-CROP","IRRIGATED","Yield rainfall",TYPE,SUBTYPE,"nan","nan"])
                writer_b.writerow(["NON-CROP","IRRIGATED","Incremental yield",TYPE,SUBTYPE,"nan","nan"])
                writer_b.writerow(["NON-CROP","IRRIGATED","Total yield",TYPE,SUBTYPE,"nan","nan"])
                if TYPE is not 'Livestock':
                    writer_a.writerow(["NON-CROP","RAINFED","ET",TYPE,SUBTYPE,"nan"])
                    writer_a.writerow(["NON-CROP","IRRIGATED","ET rainfall",TYPE,SUBTYPE,"nan"])
                    writer_a.writerow(["NON-CROP","IRRIGATED","Incremental ET",TYPE,SUBTYPE,"nan"])
                else:
                    continue
            else:
                start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WCblue, WCgreen  = read_csv(wp_y_non_crop_dictionary[TYPE][SUBTYPE])
                mask = start_dates == datetime.date(year,1,1)
                if TYPE is not 'Livestock':
                    writer_b.writerow(["NON-CROP","RAINFED","Yield",TYPE,SUBTYPE,Y[mask][0],WP[mask][0]])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Yield rainfall",TYPE,SUBTYPE,"nan","nan"])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Incremental yield",TYPE,SUBTYPE,"nan","nan"])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Total yield",TYPE,SUBTYPE,"nan","nan"])
                    writer_a.writerow(["NON-CROP","RAINFED","ET",TYPE,SUBTYPE,WC[mask][0]])
                    writer_a.writerow(["NON-CROP","IRRIGATED","ET rainfall",TYPE,SUBTYPE,"nan"])
                    writer_a.writerow(["NON-CROP","IRRIGATED","Incremental ET",TYPE,SUBTYPE,"nan"])
                else:
                    writer_b.writerow(["NON-CROP","RAINFED","Yield",TYPE,SUBTYPE,Y[mask][0],"nan"])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Yield rainfall",TYPE,SUBTYPE,"nan","nan"])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Incremental yield",TYPE,SUBTYPE,"nan","nan"])
                    writer_b.writerow(["NON-CROP","IRRIGATED","Total yield",TYPE,SUBTYPE,"nan","nan"])
    
    csv_file_b.close()
    
    return output_csv_fh_a, output_csv_fh_b

    
def calc_Y_WP_year(csv_fh, output_dir, croptype):
    """
    Calculate yearly Yields and Water Productivities from seasonal values (created with calc_Y_WP_seasons) and store
    results in a csv-file.
    
    Parameters
    ----------
    csv_fh : str
        csv_file with seasonal values (see calc_Y_WP_seasons)
    output_dir : str
        Folder to store results.
    croptype : str
        Name of the crop for which the Y and WP have been calculated.
        
    Returns
    -------
    csv_filename : str
        Path to the new csv-file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  
        
    start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WC_blue, WC_green = read_csv(csv_fh)
    
    years = np.unique(np.array([date.year for date in np.append(start_dates, end_dates)]))
    
    csv_filename = os.path.join(output_dir, 'Yearly_Yields_WPs_{0}.csv'.format(croptype))
    csv_file = open(csv_filename, 'wb')
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(["Startdate", "Enddate", "Yield [kg/ha]", "Yield_pr [kg/ha]", "Yield_irr [kg/ha]", "WP [kg/m3]", "WP_blue [kg/m3]", "WP_green [kg/m3]", "WC [km3]", "WC_blue [km3]", "WC_green [km3]"])
    
    for year in years:
        
        starts, ends = (np.array([start_date for start_date, end_date in zip(start_dates, end_dates) if start_date.year == year or end_date.year == year]),
                        np.array([end_date for start_date, end_date in zip(start_dates, end_dates) if start_date.year == year or end_date.year == year]))
    
        boundary = datetime.date(year, 1, 1)
        
        year_length = 366 if calendar.isleap(year) else 365
        
        lengths_total_season = [float(abs((end - start).days)) for start, end in zip(starts, ends)]
        
        lengths_within_year = np.array([min(year_length, abs((boundary - end).days)) - abs(min(0, (boundary - start).days)) for start, end in zip(starts, ends)])
    
        fractions = lengths_within_year / lengths_total_season
        
        y = np.sum(np.array([Y[start_dates == start][0] for start in starts]) * fractions)
        yirr = np.sum(np.array([Yirr[start_dates == start][0] for start in starts]) * fractions)
        ypr = np.sum(np.array([Ypr[start_dates == start][0] for start in starts]) * fractions)
        
        wc = np.sum(np.array([WC[start_dates == start][0] for start in starts]) * fractions)
        wcblue = np.sum(np.array([WC_blue[start_dates == start][0] for start in starts]) * fractions)
        wcgreen = np.sum(np.array([WC_green[start_dates == start][0] for start in starts]) * fractions)
        
        wp = np.average(np.array([WP[start_dates == start][0] for start in starts]), weights = fractions)
        wpblue = np.average(np.array([WPblue[start_dates == start][0] for start in starts]), weights = fractions)
        wpgreen = np.average(np.array([WPgreen[start_dates == start][0] for start in starts]), weights = fractions)
        
        writer.writerow([datetime.date(year,1,1), datetime.date(year,12,31), y, ypr, yirr, wp, wpblue, wpgreen, wc, wcblue, wcgreen])
    
    csv_file.close()
    
    return csv_filename

def import_growing_seasons(csv_fh):
    """
    Reads an csv file with dates, see example for format of the csv file.
    
    Parameters
    ----------
    csv_fh : str
        Filehandle pointing to csv-file
        
    Returns
    -------
    start_dates : ndarray
        List with datetime.date objects
    end_dates : ndarray
        List with datetime.date object
    
    Examples
    --------
    The csv file should be like:
    >>> Start;End<new_line> 
            04/11/2000;17/02/2001<new_line>
            03/05/2001;02/07/2001<new_line>
            29/11/2001;27/02/2002<new_line>
            etc.
    
    """
    start_dates = np.array([])
    end_dates = np.array([])

    with open(csv_fh) as csvfile:
         reader = csv.reader(csvfile, delimiter=';')
         for row in reader:
             if np.all([row[0] != 'Start', row[1] != 'End']):
                 start_dates = np.append(start_dates, datetime.datetime.strptime(row[0], '%d/%m/%Y').date())
                 end_dates = np.append(end_dates, datetime.datetime.strptime(row[1], '%d/%m/%Y').date())
    
    return start_dates, end_dates

def read_csv(csv_fh):
    """
    Reads and csv file generated by the function calc_Y_WP_seasons and returns the 
    values as np.arrays.
    
    Parameters
    ----------
    csv_fh : str
        Filehandle pointing to a csv-file generated by calc_Y_WP_seasons.
        
    Returns
    -------
    start_dates : ndarray
        Array containing datetime.date objects.
    end_dates : ndarray
        Array containing datetime.date objects.      
    Y : ndarray
        Array containing Yield data.
    Yirr : ndarray
        Array containing Yield from irrigation data.
    Ypr : ndarray
        Array containing Yield from precipitation data.
    WP : ndarray
        Array containing Water Productivity data.
    WPblue : ndarray
        Array containing Blue WP data.
    WPgreen : ndarray
        Array containing Green WP data.
    """
    start_dates = np.array([])
    end_dates = np.array([])
    Y = np.array([])
    Yirr = np.array([])
    Ypr = np.array([])
    WP = np.array([])
    WPblue = np.array([])
    WPgreen = np.array([])
    WC = np.array([])
    WC_green = np.array([])
    WC_blue = np.array([])
    
    with open(csv_fh) as csvfile:
         reader = csv.reader(csvfile, delimiter=';')
         for row in reader:
             if np.all([row[2] != 'nan', row[0] != 'Startdate']):
                 try:
                     start_dates = np.append(start_dates, datetime.datetime.strptime(row[0], '%Y-%m-%d').date())
                     end_dates = np.append(end_dates, datetime.datetime.strptime(row[1], '%Y-%m-%d').date())
                 except:
                     start_dates = np.append(start_dates, datetime.datetime.strptime(row[0], '%d/%m/%Y').date())
                     end_dates = np.append(end_dates, datetime.datetime.strptime(row[1], '%d/%m/%Y').date())                     
                 Y = np.append(Y, float(row[2]))
                 Ypr = np.append(Ypr, float(row[3]))
                 Yirr = np.append(Yirr, float(row[4]))
                 WP = np.append(WP, float(row[5]))
                 WPblue = np.append(WPblue, float(row[6]))
                 WPgreen = np.append(WPgreen, float(row[7]))
                 WC = np.append(WC, float(row[8]))
                 WC_blue = np.append(WC_blue, float(row[9]))
                 WC_green = np.append(WC_green, float(row[10]))
                 

    return start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WC_blue, WC_green
    
def calc_Y_WP_seasons(start_dates, end_dates, lu_fh, lu_class, croptype, etgreen_fhs, etgreen_dates, etblue_fhs, etblue_dates, ndm_fhs, ndm_dates, p_fhs, p_dates, output_dir, HIWC_dict, ab = (1.0,1.0)):
    """
    Calculate Yields and WPs per season and save results in a csv-file.
    
    Parameters
    ----------
    start_dates : ndarray
        Array with datetime.date objects specifying the startdates of the growing seasons. See ndvi_profiles.py.
    end_dates : ndarray
        Array with datetime.date objects specifying the enddates of the growing seasons. See ndvi_profiles.py.
    lu_fh : str
        Landuse map.
    lu_class : int
        Landuseclass for which to calculate Y and WP.
    croptype : str
        Name of croptype, should be present in HIWC_dict.keys().
    etgreen_fhs : ndarray
        Array with strings pointing to ETgreen maps.
    etgreen_dates : ndarray
        Array with datetime.date objects corresponding to etgreen_fhs.
    etblue_fhs : ndarray
        Array with strings pointing to ETblue maps.
    etblue_dates : ndarray
        Array with datetime.date objects corresponding to etblue_fhs.
    ndm_fhs : ndarray
        Array with strings pointing to Net-Dry-Matter maps.
    ndm_dates : ndarray
        Array with datetime.date objects corresponding to ndm_fhs.
    p_fhs : ndarray
        Array with strings pointing to P maps.
    p_dates : ndarray
        Array with datetime.date objects corresponding to p_fhs.
    output_dir : str
        Folder to save results
    HIWC_dict : dict
        Dictionary with Harvest indices and Water Contents, see get_dictionaries.get_hi_and_ec().
    ab : tuple, optional
        Two parameters used to split Yield into irrigation and precipitation yield, see split_Yield.
        
    Returns
    -------
    csv_filename : str
        Path to newly created csv-file.        
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)    
    
    csv_filename = os.path.join(output_dir, 'Yields_WPs_{0}.csv'.format(croptype))
    csv_file = open(csv_filename, 'wb')
    writer = csv.writer(csv_file, delimiter=';')
    
    writer.writerow(["Startdate", "Enddate", "Yield [kg/ha]", "Yield_pr [kg/ha]", "Yield_irr [kg/ha]", "WP [kg/m3]", "WP_blue [kg/m3]", "WP_green [kg/m3]", "WC [km3]", "WC_blue [km3]", "WC_green [km3]"])
    for startdate, enddate in zip(start_dates, end_dates):
        Yield, Yield_pr, Yield_irr, Wp, Wp_blue, Wp_green, Wc, Wc_blue, Wc_green = calc_Y_WP_season(startdate, enddate, lu_fh, lu_class, croptype, etgreen_fhs, etgreen_dates, etblue_fhs, etblue_dates, ndm_fhs, ndm_dates, p_fhs, p_dates, HIWC_dict, ab = ab, output_dir = output_dir)
        
        writer.writerow([startdate, enddate, Yield, Yield_pr, Yield_irr, Wp, Wp_blue, Wp_green, Wc, Wc_blue, Wc_green])
    
    csv_file.close()
    return csv_filename

def split_Yield(pfraction, etbfraction, a, b):
    """
    Calculate fractions to split Yield into Yield_precip and Yield _irri.
    
    Parameters
    ----------
    pfraction : ndarray
        Array of Precipitation devided by np.nanmax(P)
    etbfraction : ndarray
        Array of fraction of ETblue of total ET.
    a : float
        Parameter to define the fraction.
    b : float
        Parameter to define the fraction.
        
    Returns
    -------
    fraction : ndarray
        Array of the fraction.
    """
    fraction = -(((etbfraction-1)*a)**2 - ((pfraction-1)*b)**2) + 0.5
    fraction = np.where(fraction > 1.0, 1.0, fraction)
    fraction = np.where(fraction < 0.0, 0.0, fraction)
    return fraction
    
def calc_Y_WP_season(startdate, enddate, lu_fh, lu_class, croptype, etgreen_fhs, etgreen_dates, etblue_fhs, etblue_dates, ndm_fhs, ndm_dates, p_fhs, p_dates, HIWC_dict, ab = (1.0,1.0), output_dir = None):
    """
    Calculate Yields and WPs for one season.
    
    Parameters
    ----------
    startdate : object
        datetime.date object specifying the startdate of the growing season.
    enddate : ndarray
        datetime.date object specifying the enddate of the growing season.
    lu_fh : str
        Landuse map.
    lu_class : int
        Landuseclass for which to calculate Y and WP.
    croptype : str
        Name of croptype, should be present in HIWC_dict.keys().
    etgreen_fhs : ndarray
        Array with strings pointing to ETgreen maps.
    etgreen_dates : ndarray
        Array with datetime.date objects corresponding to etgreen_fhs.
    etblue_fhs : ndarray
        Array with strings pointing to ETblue maps.
    etblue_dates : ndarray
        Array with datetime.date objects corresponding to etblue_fhs.
    ndm_fhs : ndarray
        Array with strings pointing to Net-Dry-Matter maps.
    ndm_dates : ndarray
        Array with datetime.date objects corresponding to ndm_fhs.
    p_fhs : ndarray
        Array with strings pointing to P maps.
    p_dates : ndarray
        Array with datetime.date objects corresponding to p_fhs.
    output_dir : str
        Folder to save results
    HIWC_dict : dict
        Dictionary with Harvest indices and Water Contents, see get_dictionaries.get_hi_and_ec().
    ab : tuple, optional
        Two parameters used to split Yield into irrigation and precipitation yield, see split_Yield.
        
    Returns
    -------
    Yield : float
        The yield for the croptype.
    Yield_pr : float
        The yield_precip for the croptype.
    Yield_irr : float
        The yield_irri for the croptype.
    Wp : float
        The waterproductivity for the croptype.
    Wp_blue : float
        The blue waterproductivity for the croptype.
    Wp_green : float
        The green waterproductivity for the croptype.
    Wc : float
        The water consumption for the croptype.
    Wc_blue : float
        The blue water consumption for the croptype.
    Wc_green : float
        The green water consumption for the croptype.
    """
    common_dates = becgis.CommonDates([etblue_dates, etgreen_dates, p_dates, ndm_dates])
    
    harvest_index = HIWC_dict[croptype][0]  
    moisture_content = HIWC_dict[croptype][1]
    
    current = datetime.date(startdate.year, startdate.month, 1)
    end_month = datetime.date(enddate.year, enddate.month, 1)
    
    req_dates = np.array([current])
    while current < end_month:
        current = current + relativedelta(months = 1)
        req_dates = np.append(req_dates, current)
    
    season_complete = True
    for date in req_dates:
        season_complete = np.all([season_complete, date in common_dates])
        if not season_complete:
            print("{0} missing in input data, skipping this season".format(date))
            
    if season_complete:
    
        fractions = np.ones(np.shape(req_dates))
        
        start_month_length = float(calendar.monthrange(startdate.year, startdate.month)[1])
        end_month_length = float(calendar.monthrange(enddate.year, enddate.month)[1])
        
        fractions[0] = (start_month_length - startdate.day + 1) / start_month_length
        fractions[-1] = (enddate.day -1) / end_month_length
        
        NDMs = np.stack([becgis.OpenAsArray(ndm_fhs[ndm_dates == date][0], nan_values = True) * fraction for date, fraction in zip(req_dates, fractions)], axis=2)
        NDM = np.nansum(NDMs, axis=2)
        del NDMs
        
        ETGREENs = np.stack([becgis.OpenAsArray(etgreen_fhs[etgreen_dates == date][0], nan_values = True) * fraction for date, fraction in zip(req_dates, fractions)], axis=2)
        ETGREEN = np.nansum(ETGREENs, axis=2)
        del ETGREENs
        
        ETBLUEs = np.stack([becgis.OpenAsArray(etblue_fhs[etblue_dates == date][0], nan_values = True) * fraction for date, fraction in zip(req_dates, fractions)], axis=2)
        ETBLUE = np.nansum(ETBLUEs, axis=2)
        del ETBLUEs
        
        Ps = np.stack([becgis.OpenAsArray(p_fhs[p_dates == date][0], nan_values = True) * fraction for date, fraction in zip(req_dates, fractions)], axis=2)
        P = np.nansum(Ps, axis=2)
        del Ps
        
        LULC = becgis.OpenAsArray(lu_fh)
        
        NDM[NDM == 0] = np.nan
        NDM[LULC != lu_class] = ETBLUE[LULC != lu_class] = ETGREEN[LULC != lu_class] =  np.nan
        
        Y = (harvest_index * NDM) / (1 - moisture_content)
        
        etbfraction = ETBLUE / (ETBLUE + ETGREEN)
        pfraction = P / np.nanmax(P)
        fraction = split_Yield(pfraction, etbfraction, ab[0], ab[1])
        
        Yirr = Y * fraction
        Ypr = Y - Yirr

        if output_dir:
            x = y = np.arange(0.0, 1.1, 0.1)
            XX, YY = np.meshgrid(x, y)
            Z = split_Yield(XX,YY, ab[0], ab[1])
            plt.figure(1, figsize = (12,10))
            plt.clf()
            cmap = LinearSegmentedColormap.from_list('mycmap', ['#6bb8cc','#a3db76','#d98d8e'])
            plt.contourf(XX,YY,Z,np.arange(0.0,1.1,0.1), cmap = cmap)
            plt.colorbar(ticks = np.arange(0.0,1.1,0.1), label= 'Yirr as fraction of total Y [-]', boundaries = [0,1])
            plt.xlabel('Normalized Precipitation [-]')
            plt.ylabel('ETblue/ET [-]')
            plt.title('Split Yield into Yirr and Ypr')
            plt.suptitle('Z(X,Y) = -(((Y-1) * a)^2 - ((X-1) * b)^2) + 0.5 with a = {0:.2f} and b = {1:.2f}'.format(ab[0],ab[1]))
            plt.scatter(pfraction, etbfraction, color = 'w', label = croptype, edgecolors = 'k')
            plt.legend()
            plt.xlim((0,1))
            plt.ylim((0,1))
            plt.savefig(os.path.join(output_dir, '{0}_{1}_{2}_cloud.png'.format(croptype, req_dates[0], req_dates[-1])))

        Yield = np.nanmean(Y)
        Yield_pr = np.nanmean(Ypr)
        Yield_irr = np.nanmean(Yirr)
        
        Et_blue = np.nanmean(ETBLUE)
        Et_green = np.nanmean(ETGREEN)
        
        areas = becgis.MapPixelAreakm(lu_fh)
        Wc_blue = np.nansum(ETBLUE / 1000**2 * areas)
        Wc_green = np.nansum(ETGREEN / 1000**2 * areas)
        Wc = Wc_blue + Wc_green
        
        areas[LULC != lu_class] = np.nan
        print('{0}: {1} km2'.format(croptype, np.nansum(areas)))
        
        Wp = Yield / ((Et_blue + Et_green) * 10)
        Wp_blue = np.where(Et_blue == 0, [np.nan], [Yield_irr / (Et_blue * 10)])[0]
        Wp_green = np.where(Et_green == 0, [np.nan], [Yield_pr / (Et_green * 10)])[0]
        
    else:
        
        Yield = Yield_pr = Yield_irr = Wp = Wp_blue = Wp_green = Wc = Wc_blue = Wc_green = np.nan
        
    return Yield, Yield_pr, Yield_irr, Wp, Wp_blue, Wp_green, Wc, Wc_blue, Wc_green

def plot_Y_WP(csv_fh, output_dir, croptype = None, catchment_name = None, filetype = 'png'):
    """
    Plot yields and water productivities per season or per year.
    
    Parameters
    ----------
    csv_fh : str
        csv-file with yields and wps per season or year, can be generated with calc_Y_WP_year or with calc_Y_WP_seasons.
    output_dir : str
        folder to save graphs.
    croptype : str, optional
        String used to format the graphs.
    catchment_name : str, optional
        String used to format the graphs.
    filetype : str, optional
        filetype, default is pdf, can also choose, 'png'.    
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
            
    start_dates, end_dates, Y, Yirr, Ypr, WP, WPblue, WPgreen, WC, WCblue, WCgreen = read_csv(csv_fh)
    
    ordinal_startdates = np.array([date.toordinal() for date in start_dates])
    ordinal_enddates = np.array([date.toordinal() for date in end_dates])
    
    fig = plt.figure(1, figsize = (10,10))
    plt.clf()
    plt.grid(b=True, which='Major', color='0.65',linestyle='--', zorder = 0)
    ax = fig.add_subplot(111)
    ax.bar(start_dates, Yirr, ordinal_enddates-ordinal_startdates, color = '#6bb8cc', label = 'Yield from irrigation', linewidth = 2, edgecolor = 'w')
    ax.bar(start_dates, Ypr, ordinal_enddates-ordinal_startdates, bottom = Yirr, color = '#a3db76', label = 'Yield from precipitation', linewidth = 2, edgecolor = 'w')
    ax.set_title('Seasonal Yield, {0} in {1}'.format(croptype, catchment_name))
    ax.set_xlabel('Time')
    ax.set_ylabel('Yield [kg/ha]')
    [r.set_zorder(10) for r in ax.spines.itervalues()]
    fig.autofmt_xdate()
    ax.legend(loc = 'upper left',fancybox=True, shadow=True)
    ax.set_ylim([0, np.max(Y) * 1.2])
    plt.savefig(os.path.join(output_dir,'{0}_yields.{1}'.format(croptype,filetype)))
    
    ordinal_meandates = np.mean([ordinal_startdates, ordinal_enddates], axis=0)

    fig = plt.figure(2, figsize = (10,10))
    plt.clf()
    plt.grid(b=True, which='Major', color='0.65',linestyle='--', zorder = 0)
    ax = fig.add_subplot(111)
    red_patch = mpatches.Patch(color='#d98d8e', label='WP')
    blue_line = mlines.Line2D([], [], color='#6bb8cc', label='WPblue', lw = 3)
    green_line = mlines.Line2D([], [], color='#a3db76', label='WPgreen', lw = 3)
    ax.legend(handles=[red_patch,blue_line, green_line],loc = 'upper left',fancybox=True, shadow=True)
    ax.bar(ordinal_meandates, WPblue, color = 'w', linewidth = 2, edgecolor = 'w', xerr = (ordinal_enddates-ordinal_startdates)/2.2, ecolor = '#6bb8cc', capsize = 0, error_kw = {'lw': 3})
    ax.bar(ordinal_meandates, WPgreen, color = 'w', linewidth = 2, edgecolor = 'w', xerr = (ordinal_enddates-ordinal_startdates)/2.2, ecolor = '#a3db76', capsize = 0, error_kw = {'lw': 3})
    ax.bar(start_dates, WP, ordinal_enddates-ordinal_startdates, color = '#d98d8e', label = 'WP', linewidth = 2, edgecolor = 'w')
    ax.set_title('Seasonal Water Productivity, {0} in {1}'.format(croptype, catchment_name))
    ax.set_ylabel('Water Productivity [kg/m3]')
    ax.set_xlabel('Time')
    ax.set_ylim([0, max(max(WP), max(WPblue), max(WPgreen)) *1.2])
    fig.autofmt_xdate()
    [r.set_zorder(10) for r in ax.spines.itervalues()]
    plt.savefig(os.path.join(output_dir,'{0}_wps.{1}'.format(croptype,filetype)))    

import pandas as pd
import xml.etree.ElementTree as ET
import subprocess

def create_sheet3_png(basin, period, units, data, output, template=False):

    # Read table

    df1 = pd.read_csv(data[0], sep=';')
    df2 = pd.read_csv(data[1], sep=';')

    # Data frames

    df1c = df1.loc[df1.USE == "CROP"]
    df1n = df1.loc[df1.USE == "NON-CROP"]

    df2c = df2.loc[df2.USE == "CROP"]
    df2n = df2.loc[df2.USE == "NON-CROP"]

    # Read csv file part 1
    crop_r01c01 = float(df1c.loc[(df1c.TYPE == "Cereals") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c01 = float(df1c.loc[(df1c.TYPE == "Cereals") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c01 = float(df1c.loc[(df1c.TYPE == "Cereals") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c01 = crop_r02c01 + crop_r03c01

    crop_r01c02 = float(df1c.loc[(df1c.SUBTYPE == "Root/tuber crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c02 = float(df1c.loc[(df1c.SUBTYPE == "Root/tuber crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c02 = float(df1c.loc[(df1c.SUBTYPE == "Root/tuber crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c02 = crop_r02c02 + crop_r03c02

    crop_r01c03 = float(df1c.loc[(df1c.SUBTYPE == "Leguminous crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c03 = float(df1c.loc[(df1c.SUBTYPE == "Leguminous crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c03 = float(df1c.loc[(df1c.SUBTYPE == "Leguminous crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c03 = crop_r02c03 + crop_r03c03

    crop_r01c04 = float(df1c.loc[(df1c.SUBTYPE == "Sugar crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c04 = float(df1c.loc[(df1c.SUBTYPE == "Sugar crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c04 = float(df1c.loc[(df1c.SUBTYPE == "Sugar crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c04 = crop_r02c04 + crop_r03c04

    crop_r01c05 = float(df1c.loc[(df1c.TYPE == "Non-cereals") &
                        (df1c.SUBCLASS == "ET") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r02c05 = float(df1c.loc[(df1c.TYPE == "Non-cereals") &
                        (df1c.SUBCLASS == "ET rainfall") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r03c05 = float(df1c.loc[(df1c.TYPE == "Non-cereals") &
                        (df1c.SUBCLASS == "Incremental ET") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r04c05 = crop_r02c05 + crop_r03c05

    crop_r01c06 = float(df1c.loc[(df1c.SUBTYPE == "Vegetables & melons") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c06 = float(df1c.loc[(df1c.SUBTYPE == "Vegetables & melons") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c06 = float(df1c.loc[(df1c.SUBTYPE == "Vegetables & melons") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c06 = crop_r02c06 + crop_r03c06

    crop_r01c07 = float(df1c.loc[(df1c.SUBTYPE == "Fruits & nuts") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c07 = float(df1c.loc[(df1c.SUBTYPE == "Fruits & nuts") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c07 = float(df1c.loc[(df1c.SUBTYPE == "Fruits & nuts") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c07 = crop_r02c07 + crop_r03c07

    crop_r01c08 = float(df1c.loc[(df1c.TYPE == "Fruit & vegetables") &
                        (df1c.SUBCLASS == "ET") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r02c08 = float(df1c.loc[(df1c.TYPE == "Fruit & vegetables") &
                        (df1c.SUBCLASS == "ET rainfall") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r03c08 = float(df1c.loc[(df1c.TYPE == "Fruit & vegetables") &
                        (df1c.SUBCLASS == "Incremental ET") &
                        (df1c.SUBTYPE == "Merged")].WATER_CONSUMPTION)
    crop_r04c08 = crop_r02c08 + crop_r03c08

    crop_r01c09 = float(df1c.loc[(df1c.TYPE == "Oilseeds") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c09 = float(df1c.loc[(df1c.TYPE == "Oilseeds") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c09 = float(df1c.loc[(df1c.TYPE == "Oilseeds") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c09 = crop_r02c09 + crop_r03c09

    crop_r01c10 = float(df1c.loc[(df1c.TYPE == "Feed crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c10 = float(df1c.loc[(df1c.TYPE == "Feed crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c10 = float(df1c.loc[(df1c.TYPE == "Feed crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c10 = crop_r02c10 + crop_r03c10

    crop_r01c11 = float(df1c.loc[(df1c.TYPE == "Beverage crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c11 = float(df1c.loc[(df1c.TYPE == "Beverage crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c11 = float(df1c.loc[(df1c.TYPE == "Beverage crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c11 = crop_r02c11 + crop_r03c11

    crop_r01c12 = float(df1c.loc[(df1c.TYPE == "Other crops") &
                        (df1c.SUBCLASS == "ET")].WATER_CONSUMPTION)
    crop_r02c12 = float(df1c.loc[(df1c.TYPE == "Other crops") &
                        (df1c.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    crop_r03c12 = float(df1c.loc[(df1c.TYPE == "Other crops") &
                        (df1c.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    crop_r04c12 = crop_r02c12 + crop_r03c12

    noncrop_r01c01 = float(df1n.loc[(df1n.TYPE == "Fish (Aquaculture)") &
                           (df1n.SUBCLASS == "ET")].WATER_CONSUMPTION)
    noncrop_r02c01 = float(df1n.loc[(df1n.TYPE == "Fish (Aquaculture)") &
                           (df1n.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    noncrop_r03c01 = float(df1n.loc[(df1n.TYPE == "Fish (Aquaculture)") &
                           (df1n.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    noncrop_r04c01 = noncrop_r02c01 + noncrop_r03c01

    noncrop_r01c02 = float(df1n.loc[(df1n.TYPE == "Timber") &
                           (df1n.SUBCLASS == "ET")].WATER_CONSUMPTION)
    noncrop_r02c02 = float(df1n.loc[(df1n.TYPE == "Timber") &
                           (df1n.SUBCLASS == "ET rainfall")].WATER_CONSUMPTION)
    noncrop_r03c02 = float(df1n.loc[(df1n.TYPE == "Timber") &
                           (df1n.SUBCLASS == "Incremental ET")].WATER_CONSUMPTION)
    noncrop_r04c02 = noncrop_r02c02 + noncrop_r03c02

    crop_r01 = pd.np.nansum([crop_r01c01, crop_r01c02, crop_r01c03,
                             crop_r01c04, crop_r01c05, crop_r01c06,
                             crop_r01c07, crop_r01c08, crop_r01c09,
                             crop_r01c10, crop_r01c11, crop_r01c12])

    crop_r02 = pd.np.nansum([crop_r02c01, crop_r02c02, crop_r02c03,
                             crop_r02c04, crop_r02c05, crop_r02c06,
                             crop_r02c07, crop_r02c08, crop_r02c09,
                             crop_r02c10, crop_r02c11, crop_r02c12])

    crop_r03 = pd.np.nansum([crop_r03c01, crop_r03c02, crop_r03c03,
                             crop_r03c04, crop_r03c05, crop_r03c06,
                             crop_r03c07, crop_r03c08, crop_r03c09,
                             crop_r03c10, crop_r03c11, crop_r03c12])

    crop_r04 = crop_r02 + crop_r03

    noncrop_r01 = pd.np.nansum([noncrop_r01c01, noncrop_r01c02])

    noncrop_r02 = pd.np.nansum([noncrop_r02c01, noncrop_r02c02])

    noncrop_r03 = pd.np.nansum([noncrop_r03c01, noncrop_r03c02])

    noncrop_r04 = noncrop_r02 + noncrop_r03

    ag_water_cons = crop_r01 + crop_r04 + noncrop_r01 + noncrop_r04

    # Read csv file part 2
    # Land productivity
    lp_r01c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r02c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Yield rainfall") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r03c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Incremental yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r04c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Total yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)

    lp_r01c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r02c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Yield rainfall") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r03c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Incremental yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)
    lp_r04c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Total yield") &
                      (df2c.SUBTYPE == "Merged")].LAND_PRODUCTIVITY)

    lp_r01c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r01c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r02c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r03c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r04c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r05c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r06c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r07c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r08c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r05c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r06c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r07c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r08c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r05c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r06c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r07c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r08c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    lp_r05c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Yield")].LAND_PRODUCTIVITY)
    lp_r06c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Yield rainfall")].LAND_PRODUCTIVITY)
    lp_r07c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Incremental yield")].LAND_PRODUCTIVITY)
    lp_r08c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Total yield")].LAND_PRODUCTIVITY)

    # Water productivity
    wp_r01c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c01 = float(df2c.loc[(df2c.TYPE == "Cereals") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c02 = float(df2c.loc[(df2c.SUBTYPE == "Root/tuber crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c03 = float(df2c.loc[(df2c.SUBTYPE == "Leguminous crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)
    
    wp_r01c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c04 = float(df2c.loc[(df2c.SUBTYPE == "Sugar crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r02c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Yield rainfall") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r03c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Incremental yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r04c05 = float(df2c.loc[(df2c.TYPE == "Non-cereals") &
                      (df2c.SUBCLASS == "Total yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)

    wp_r01c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c06 = float(df2c.loc[(df2c.SUBTYPE == "Vegetables & melons") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c07 = float(df2c.loc[(df2c.SUBTYPE == "Fruits & nuts") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r02c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Yield rainfall") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r03c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Incremental yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)
    wp_r04c08 = float(df2c.loc[(df2c.TYPE == "Fruit & vegetables") &
                      (df2c.SUBCLASS == "Total yield") &
                      (df2c.SUBTYPE == "Merged")].WATER_PRODUCTIVITY)

    wp_r01c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c09 = float(df2c.loc[(df2c.TYPE == "Oilseeds") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c10 = float(df2c.loc[(df2c.TYPE == "Feed crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c11 = float(df2c.loc[(df2c.TYPE == "Beverage crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r01c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r02c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r03c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r04c12 = float(df2c.loc[(df2c.TYPE == "Other crops") &
                      (df2c.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r05c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r06c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r07c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r08c01 = float(df2n.loc[(df2n.SUBTYPE == "Meat") &
                      (df2n.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r05c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r06c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r07c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r08c02 = float(df2n.loc[(df2n.SUBTYPE == "Milk") &
                      (df2n.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r05c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r06c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r07c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r08c03 = float(df2n.loc[(df2n.TYPE == "Fish (Aquaculture)") &
                      (df2n.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    wp_r05c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Yield")].WATER_PRODUCTIVITY)
    wp_r06c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Yield rainfall")].WATER_PRODUCTIVITY)
    wp_r07c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Incremental yield")].WATER_PRODUCTIVITY)
    wp_r08c04 = float(df2n.loc[(df2n.TYPE == "Timber") &
                      (df2n.SUBCLASS == "Total yield")].WATER_PRODUCTIVITY)

    # Calculations & modify svgs
    if not template:
        path = os.path.dirname(os.path.abspath(__file__))
        svg_template_path_1 = os.path.join(path, 'svg', 'sheet_3_part1.svg')
        svg_template_path_2 = os.path.join(path, 'svg', 'sheet_3_part2.svg')
    else:
        svg_template_path_1 = os.path.abspath(template[0])
        svg_template_path_2 = os.path.abspath(template[1])

    tree1 = ET.parse(svg_template_path_1)
    tree2 = ET.parse(svg_template_path_2)
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Titles

    xml_txt_box = tree1.findall('''.//*[@id='basin']''')[0]
    xml_txt_box.getchildren()[0].text = 'Basin: ' + basin

    xml_txt_box = tree1.findall('''.//*[@id='period']''')[0]
    xml_txt_box.getchildren()[0].text = 'Period: ' + period

    xml_txt_box = tree1.findall('''.//*[@id='units']''')[0]
    xml_txt_box.getchildren()[0].text = 'Part 1: Agricultural water consumption (' + units[0] + ')'

    xml_txt_box = tree2.findall('''.//*[@id='basin2']''')[0]
    xml_txt_box.getchildren()[0].text = 'Basin: ' + basin

    xml_txt_box = tree2.findall('''.//*[@id='period2']''')[0]
    xml_txt_box.getchildren()[0].text = 'Period: ' + period

    xml_txt_box = tree2.findall('''.//*[@id='units2']''')[0]
    xml_txt_box.getchildren()[0].text = 'Part 2: Land productivity (' + units[1] + ') and water productivity (' + units[2] + ')'

    # Part 1
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c01']''')[0]
    if not pd.isnull(crop_r01c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c02']''')[0]
    if not pd.isnull(crop_r01c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c03']''')[0]
    if not pd.isnull(crop_r01c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c04']''')[0]
    if not pd.isnull(crop_r01c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c05']''')[0]
    if not pd.isnull(crop_r01c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c06']''')[0]
    if not pd.isnull(crop_r01c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c07']''')[0]
    if not pd.isnull(crop_r01c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c08']''')[0]
    if not pd.isnull(crop_r01c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c09']''')[0]
    if not pd.isnull(crop_r01c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c10']''')[0]
    if not pd.isnull(crop_r01c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c11']''')[0]
    if not pd.isnull(crop_r01c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01c12']''')[0]
    if not pd.isnull(crop_r01c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r01']''')[0]
    if not pd.isnull(crop_r01):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c01']''')[0]
    if not pd.isnull(crop_r02c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c02']''')[0]
    if not pd.isnull(crop_r02c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c03']''')[0]
    if not pd.isnull(crop_r02c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c04']''')[0]
    if not pd.isnull(crop_r02c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c05']''')[0]
    if not pd.isnull(crop_r02c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c06']''')[0]
    if not pd.isnull(crop_r02c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c07']''')[0]
    if not pd.isnull(crop_r02c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c08']''')[0]
    if not pd.isnull(crop_r02c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c09']''')[0]
    if not pd.isnull(crop_r02c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c10']''')[0]
    if not pd.isnull(crop_r02c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c11']''')[0]
    if not pd.isnull(crop_r02c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02c12']''')[0]
    if not pd.isnull(crop_r02c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r02']''')[0]
    if not pd.isnull(crop_r02):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c01']''')[0]
    if not pd.isnull(crop_r03c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c02']''')[0]
    if not pd.isnull(crop_r03c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c03']''')[0]
    if not pd.isnull(crop_r03c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c04']''')[0]
    if not pd.isnull(crop_r03c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c05']''')[0]
    if not pd.isnull(crop_r03c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c06']''')[0]
    if not pd.isnull(crop_r03c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c07']''')[0]
    if not pd.isnull(crop_r03c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c08']''')[0]
    if not pd.isnull(crop_r03c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c09']''')[0]
    if not pd.isnull(crop_r03c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c10']''')[0]
    if not pd.isnull(crop_r03c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c11']''')[0]
    if not pd.isnull(crop_r03c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03c12']''')[0]
    if not pd.isnull(crop_r03c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r03']''')[0]
    if not pd.isnull(crop_r03):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c01']''')[0]
    if not pd.isnull(crop_r04c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c02']''')[0]
    if not pd.isnull(crop_r04c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c03']''')[0]
    if not pd.isnull(crop_r04c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c04']''')[0]
    if not pd.isnull(crop_r04c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c05']''')[0]
    if not pd.isnull(crop_r04c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c06']''')[0]
    if not pd.isnull(crop_r04c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c07']''')[0]
    if not pd.isnull(crop_r04c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c08']''')[0]
    if not pd.isnull(crop_r04c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c09']''')[0]
    if not pd.isnull(crop_r04c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c10']''')[0]
    if not pd.isnull(crop_r04c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c11']''')[0]
    if not pd.isnull(crop_r04c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04c12']''')[0]
    if not pd.isnull(crop_r04c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='crop_r04']''')[0]
    if not pd.isnull(crop_r04):
        xml_txt_box.getchildren()[0].text = '%.2f' % crop_r04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r01c01']''')[0]
    if not pd.isnull(noncrop_r01c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r01c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r01c02']''')[0]
    if not pd.isnull(noncrop_r01c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r01c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r01']''')[0]
    if not pd.isnull(noncrop_r01) and noncrop_r01 > 0.001:
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r02c01']''')[0]
    if not pd.isnull(noncrop_r02c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r02c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r02c02']''')[0]
    if not pd.isnull(noncrop_r02c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r02c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r02']''')[0]
    if not pd.isnull(noncrop_r02) and noncrop_r02 > 0.001:
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r03c01']''')[0]
    if not pd.isnull(noncrop_r03c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r03c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r03c02']''')[0]
    if not pd.isnull(noncrop_r03c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r03c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r03']''')[0]
    if not pd.isnull(noncrop_r03) and noncrop_r03 > 0.001:
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r04c01']''')[0]
    if not pd.isnull(noncrop_r04c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r04c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r04c02']''')[0]
    if not pd.isnull(noncrop_r04c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r04c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree1.findall('''.//*[@id='noncrop_r04']''')[0]
    if not pd.isnull(noncrop_r04) and noncrop_r04 > 0.001:
        xml_txt_box.getchildren()[0].text = '%.2f' % noncrop_r04
    else:
        xml_txt_box.getchildren()[0].text = '-'

    # Part 2
    xml_txt_box = tree1.findall('''.//*[@id='ag_water_cons']''')[0]
    if not pd.isnull(ag_water_cons):
        xml_txt_box.getchildren()[0].text = '%.2f' % ag_water_cons
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c01']''')[0]
    if not pd.isnull(lp_r01c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c02']''')[0]
    if not pd.isnull(lp_r01c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c03']''')[0]
    if not pd.isnull(lp_r01c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c04']''')[0]
    if not pd.isnull(lp_r01c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c05']''')[0]
    if not pd.isnull(lp_r01c05):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c06']''')[0]
    if not pd.isnull(lp_r01c06):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c07']''')[0]
    if not pd.isnull(lp_r01c07):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c08']''')[0]
    if not pd.isnull(lp_r01c08):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c09']''')[0]
    if not pd.isnull(lp_r01c09):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c10']''')[0]
    if not pd.isnull(lp_r01c10):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c11']''')[0]
    if not pd.isnull(lp_r01c11):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r01c12']''')[0]
    if not pd.isnull(lp_r01c12):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r01c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c01']''')[0]
    if not pd.isnull(lp_r02c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c02']''')[0]
    if not pd.isnull(lp_r02c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c03']''')[0]
    if not pd.isnull(lp_r02c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c04']''')[0]
    if not pd.isnull(lp_r02c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c05']''')[0]
    if not pd.isnull(lp_r02c05):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c06']''')[0]
    if not pd.isnull(lp_r02c06):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c07']''')[0]
    if not pd.isnull(lp_r02c07):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c08']''')[0]
    if not pd.isnull(lp_r02c08):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c09']''')[0]
    if not pd.isnull(lp_r02c09):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c10']''')[0]
    if not pd.isnull(lp_r02c10):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c11']''')[0]
    if not pd.isnull(lp_r02c11):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r02c12']''')[0]
    if not pd.isnull(lp_r02c12):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r02c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c01']''')[0]
    if not pd.isnull(lp_r03c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c02']''')[0]
    if not pd.isnull(lp_r03c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c03']''')[0]
    if not pd.isnull(lp_r03c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c04']''')[0]
    if not pd.isnull(lp_r03c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c05']''')[0]
    if not pd.isnull(lp_r03c05):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c06']''')[0]
    if not pd.isnull(lp_r03c06):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c07']''')[0]
    if not pd.isnull(lp_r03c07):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c08']''')[0]
    if not pd.isnull(lp_r03c08):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c09']''')[0]
    if not pd.isnull(lp_r03c09):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c10']''')[0]
    if not pd.isnull(lp_r03c10):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c11']''')[0]
    if not pd.isnull(lp_r03c11):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r03c12']''')[0]
    if not pd.isnull(lp_r03c12):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r03c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c01']''')[0]
    if not pd.isnull(lp_r04c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c02']''')[0]
    if not pd.isnull(lp_r04c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c03']''')[0]
    if not pd.isnull(lp_r04c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c04']''')[0]
    if not pd.isnull(lp_r04c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c05']''')[0]
    if not pd.isnull(lp_r04c05):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c06']''')[0]
    if not pd.isnull(lp_r04c06):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c07']''')[0]
    if not pd.isnull(lp_r04c07):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c08']''')[0]
    if not pd.isnull(lp_r04c08):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c09']''')[0]
    if not pd.isnull(lp_r04c09):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c10']''')[0]
    if not pd.isnull(lp_r04c10):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c11']''')[0]
    if not pd.isnull(lp_r04c11):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r04c12']''')[0]
    if not pd.isnull(lp_r04c12):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r04c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c01']''')[0]
    if not pd.isnull(wp_r01c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c02']''')[0]
    if not pd.isnull(wp_r01c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c03']''')[0]
    if not pd.isnull(wp_r01c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c04']''')[0]
    if not pd.isnull(wp_r01c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c05']''')[0]
    if not pd.isnull(wp_r01c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c06']''')[0]
    if not pd.isnull(wp_r01c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c07']''')[0]
    if not pd.isnull(wp_r01c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c08']''')[0]
    if not pd.isnull(wp_r01c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c09']''')[0]
    if not pd.isnull(wp_r01c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c10']''')[0]
    if not pd.isnull(wp_r01c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c11']''')[0]
    if not pd.isnull(wp_r01c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r01c12']''')[0]
    if not pd.isnull(wp_r01c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r01c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c01']''')[0]
    if not pd.isnull(wp_r02c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c02']''')[0]
    if not pd.isnull(wp_r02c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c03']''')[0]
    if not pd.isnull(wp_r02c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c04']''')[0]
    if not pd.isnull(wp_r02c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c05']''')[0]
    if not pd.isnull(wp_r02c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c06']''')[0]
    if not pd.isnull(wp_r02c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c07']''')[0]
    if not pd.isnull(wp_r02c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c08']''')[0]
    if not pd.isnull(wp_r02c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c09']''')[0]
    if not pd.isnull(wp_r02c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c10']''')[0]
    if not pd.isnull(wp_r02c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c11']''')[0]
    if not pd.isnull(wp_r02c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r02c12']''')[0]
    if not pd.isnull(wp_r02c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r02c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c01']''')[0]
    if not pd.isnull(wp_r03c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c02']''')[0]
    if not pd.isnull(wp_r03c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c03']''')[0]
    if not pd.isnull(wp_r03c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c04']''')[0]
    if not pd.isnull(wp_r03c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c05']''')[0]
    if not pd.isnull(wp_r03c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c06']''')[0]
    if not pd.isnull(wp_r03c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c07']''')[0]
    if not pd.isnull(wp_r03c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c08']''')[0]
    if not pd.isnull(wp_r03c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c09']''')[0]
    if not pd.isnull(wp_r03c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c10']''')[0]
    if not pd.isnull(wp_r03c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c11']''')[0]
    if not pd.isnull(wp_r03c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r03c12']''')[0]
    if not pd.isnull(wp_r03c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r03c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c01']''')[0]
    if not pd.isnull(wp_r04c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c02']''')[0]
    if not pd.isnull(wp_r04c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c03']''')[0]
    if not pd.isnull(wp_r04c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c04']''')[0]
    if not pd.isnull(wp_r04c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c05']''')[0]
    if not pd.isnull(wp_r04c05):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c05
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c06']''')[0]
    if not pd.isnull(wp_r04c06):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c06
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c07']''')[0]
    if not pd.isnull(wp_r04c07):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c07
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c08']''')[0]
    if not pd.isnull(wp_r04c08):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c08
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c09']''')[0]
    if not pd.isnull(wp_r04c09):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c09
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c10']''')[0]
    if not pd.isnull(wp_r04c10):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c10
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c11']''')[0]
    if not pd.isnull(wp_r04c11):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c11
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r04c12']''')[0]
    if not pd.isnull(wp_r04c12):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r04c12
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r05c01']''')[0]
    if not pd.isnull(lp_r05c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r05c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r05c02']''')[0]
    if not pd.isnull(lp_r05c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r05c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r05c03']''')[0]
    if not pd.isnull(lp_r05c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r05c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r05c04']''')[0]
    if not pd.isnull(lp_r05c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r05c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r06c01']''')[0]
    if not pd.isnull(lp_r06c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r06c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r06c02']''')[0]
    if not pd.isnull(lp_r06c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r06c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r06c03']''')[0]
    if not pd.isnull(lp_r06c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r06c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r06c04']''')[0]
    if not pd.isnull(lp_r06c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r06c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r07c01']''')[0]
    if not pd.isnull(lp_r07c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r07c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r07c02']''')[0]
    if not pd.isnull(lp_r07c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r07c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r07c03']''')[0]
    if not pd.isnull(lp_r07c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r07c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r07c04']''')[0]
    if not pd.isnull(lp_r07c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r07c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r08c01']''')[0]
    if not pd.isnull(lp_r08c01):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r08c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r08c02']''')[0]
    if not pd.isnull(lp_r08c02):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r08c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r08c03']''')[0]
    if not pd.isnull(lp_r08c03):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r08c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='lp_r08c04']''')[0]
    if not pd.isnull(lp_r08c04):
        xml_txt_box.getchildren()[0].text = '%.0f' % lp_r08c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r05c01']''')[0]
    if not pd.isnull(wp_r05c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r05c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r05c02']''')[0]
    if not pd.isnull(wp_r05c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r05c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r05c03']''')[0]
    if not pd.isnull(wp_r05c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r05c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r05c04']''')[0]
    if not pd.isnull(wp_r05c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r05c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r06c01']''')[0]
    if not pd.isnull(wp_r06c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r06c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r06c02']''')[0]
    if not pd.isnull(wp_r06c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r06c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r06c03']''')[0]
    if not pd.isnull(wp_r06c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r06c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r06c04']''')[0]
    if not pd.isnull(wp_r06c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r06c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r07c01']''')[0]
    if not pd.isnull(wp_r07c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r07c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r07c02']''')[0]
    if not pd.isnull(wp_r07c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r07c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r07c03']''')[0]
    if not pd.isnull(wp_r07c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r07c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r07c04']''')[0]
    if not pd.isnull(wp_r07c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r07c04
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r08c01']''')[0]
    if not pd.isnull(wp_r08c01):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r08c01
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r08c02']''')[0]
    if not pd.isnull(wp_r08c02):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r08c02
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r08c03']''')[0]
    if not pd.isnull(wp_r08c03):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r08c03
    else:
        xml_txt_box.getchildren()[0].text = '-'
    xml_txt_box = tree2.findall('''.//*[@id='wp_r08c04']''')[0]
    if not pd.isnull(wp_r08c04):
        xml_txt_box.getchildren()[0].text = '%.2f' % wp_r08c04
    else:
        xml_txt_box.getchildren()[0].text = '-'

    # svg to string
    ET.register_namespace("", "http://www.w3.org/2000/svg")

    # Get the paths based on the environment variable
    #WA_env_paths = os.environ["WA_PATHS"].split(';')
    #Inkscape_env_path = WA_env_paths[1]
    Path_Inkscape = get_path('inkscape')

    # Export svg to png
    tempout_path = output[0].replace('.png', '_temporary.svg')
    tree1.write(tempout_path)
    subprocess.call([Path_Inkscape,tempout_path,'--export-png='+output[0], '-d 300'])
    os.remove(tempout_path)

        # Export svg to png
    tempout_path = output[1].replace('.png', '_temporary.svg')
    tree2.write(tempout_path)
    subprocess.call([Path_Inkscape,tempout_path,'--export-png='+output[1], '-d 300'])
    os.remove(tempout_path)

    return output

def summarize_subcrops(WP_Y_Yearly_csvs_list,output_dir,crop_subclass):
    '''
    for each LUWA sub-class that contain several sub-crops
    csv was computed for each sub-crop
    then summarize to the same sub-class
    '''
    summary=0
    n=len(WP_Y_Yearly_csvs_list)
    for csvf in WP_Y_Yearly_csvs_list:
        df=pd.read_csv(csvf,sep=';',index_col=(0,1),na_values='nan')
        summary+=df
    summary=summary/n
    summary['WC [km3]']=summary['WC [km3]']*n
    summary['WC_blue [km3]']=summary['WC_blue [km3]']*n
    summary['WC_green [km3]']=summary['WC_green [km3]']*n
    csv_filename = os.path.join(output_dir, 'Yearly_Yields_WPs_{0}.csv'.format(crop_subclass))
    summary.to_csv(csv_filename,sep=';',na_rep='nan')
    return csv_filename