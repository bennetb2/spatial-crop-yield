#!/usr/bin/env python
import sys
import re
import json
import pandas as pd
import geopandas
import numpy as np
from shapely.geometry import Point, Polygon

# Step 1: SPATIALLY FILTER: Data filtered based on the field coordinates
def filter_field_boundaries(cfg):
    # Creating a polygon for each field in config
    field_corners = {}
    for field in cfg['field_boundaries']:
        field_corners[field['name']] =  Polygon(
                            [(field['NW_corner']['latitude'],field['NW_corner']['longitude']),
                            (field['NE_corner']['latitude'], field['NE_corner']['longitude']),
                            (field['SE_corner']['latitude'], field['SE_corner']['longitude']),
                            (field['SW_corner']['latitude'], field['SW_corner']['longitude'])])

    # Geopandas library accounts for geometry of the polygons and land surfaces
    field_polygons = geopandas.GeoSeries(field_corners)

    df = pd.read_csv(cfg['csv_filepath'])

    # Storing all points located within the field polygons
    filtered_points = {}
    for field in cfg['field_boundaries']:
        # Adding points to the filtered_points object within lists identified by field name
        filtered_points[field['name']] = []

    for index, row in df.iterrows():
        try:
            # Iterating through rows of csv, creating a geopandas point using the df info
            point = Point(float(row['lat']), float(row['long']))

            # Iterating through each named field w/in the filtered_points object
            for field_name in filtered_points:
                # If the point is within the field, and does not contain zeros, add to that field
                if field_polygons[field_name].intersects(point) and not np.isnan(point.x) and not np.isnan(point.y):
                    # Append statement creates an object including the lat/long and weight for included points
                    filtered_points[field_name].append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except:
            pass
    return filtered_points
    # filtered_points is now an object filled with lists of points within fields, and identified by field name

# Step 2: PROCESS WEIGHT: Steps through data using a spatial increment to calculate change in weight
def process_weight(cfg, filtered_points):
    harvest_yield = {}  # object set up like filtered_points, to store lists identified by field names

    # Iterating through each field in the config
    for field in cfg['field_boundaries']:

        field_name = field['name']

        # Storing the calculated "yields," or changes in weight, as lists under each field name
        harvest_yield[field_name] = []

        # Setting an initial point to calculate distance for the delta weight calculation
        initial_point = filtered_points[field_name][0]
        # Iterating through each point in the specific field the for loop above is at
        for i in range(0, len(filtered_points[field_name])):

            # Defining the initial point and intermediate point as geopandas GeoSeries to allow for accurate distance calc
            initial_point_series = geopandas.GeoSeries({'point': Point(float(initial_point['latitude']), float(initial_point['longitude']))})
            i_point_series = geopandas.GeoSeries({'point': Point(float(filtered_points[field_name][i]['latitude']), float(filtered_points[field_name][i]['longitude']))})
            # Calc distance between the intial point and intermediate point, allows for checking if distance interval is met yet
            distance = initial_point_series.distance(i_point_series)['point']

            # Once distance traveled exceeds the defined distance interval, then delta weight calculation happens
            if distance > cfg['distance_interval']:
                try:
                    # Center point between initial point and intermediate point set up for delta weight
                    midpoint = initial_point_series.union(i_point_series).centroid

                    # Removing anything that isn't a decimal point or a digit from recorded weights
                    i_weight = float(re.sub('[^A-Za-z0-9.]+', '', filtered_points[field_name][i]['weight']))
                    initial_weight = float(re.sub('[^A-Za-z0-9.]+', '', initial_point['weight']))

                    # Calculating change in weight between initial point and next "step" in space
                    delta_weight = i_weight - initial_weight

                    # Saving the delta weight to field's list w/in harvest_yield object IF the change in weight is reasonable
                    # "Reasonable" currently defined as not extremely large or negative
                    # if delta < 300 and delta > -500:

                    # Append statement: appending objects containing lat/long/delta_weight to the field_name idenitified list
                    harvest_yield[field_name].append({'lat': midpoint.x['point'], 'long': midpoint.y['point'], 'delta_weight': delta_weight}) # not dividing by distance

                    # Reset initial point for next run-through
                    initial_point = filtered_points[field_name][i]
                except:
                    pass
        # # Normalizing the delta weight by finding maximum value and dividing to create a percent/ratio
        # max_weight = max([point['delta_weight'] for point in harvest_yield[field_name]])
        # for field_yield in harvest_yield[field_name]:
        #     field_yield['delta_weight'] = field_yield['delta_weight']/max_weight

    return harvest_yield

# Running all functions!
def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        filtered_points = filter_field_boundaries(cfg)
        processed_weight = process_weight(cfg, filtered_points)

        # Output csv files with delta weight points for all fields
        for field in output:
            Output_df = pd.DataFrame(data=output[field])
            Output_df.to_csv(f'{field}.csv', index=False)


if __name__ == '__main__':
    sys.exit(main())
