#!/usr/bin/env python
import sys
import json
import pandas as pd
import geopandas
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
    fields = geopandas.GeoSeries(field_corners)
    df = pd.read_csv(cfg['csv_filepath'])
    # Storing all points located within the field polygons
    filtered_points = []
    for index, row in df.iterrows():
        try:
            point = Point(float(row['lat']), float(row['long']))
            # If the point is in any defined field, keep the value
            if any(fields.intersects(point)):
                # Append statement creates an object including the lat/long and weight for included points
                filtered_points.append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except:
            pass
    return filtered_points

# Step 2: DELTA WEIGHT: Steps through data using a spatial increment to calculate change in weight


def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        filtered_points = filter_field_boundaries(cfg)

        # Creating an output csv after Step 1 to check progress
        Output_df = pd.DataFrame(data=filtered_points)
        Output_df.to_csv('test.csv', index=False)


if __name__ == '__main__':
    sys.exit(main())
