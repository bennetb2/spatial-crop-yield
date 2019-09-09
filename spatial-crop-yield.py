#!/usr/bin/env python
import sys
import json
import pandas as pd
import geopandas
from shapely.geometry import Point, Polygon

# Step 1: SPATIALLY FILTER: Data filtered based on defined polygon for the field coordinates
def filter_field_boundaries(cfg):
    # Defining the corners of the field using latitude/longitude coordinates to create a polygon
    # Geopandas library accounts for geometry of the polygons and land surfaces
    fields = geopandas.GeoSeries({
    # Fields 1 and 2 call on the manually entered points in the config file
    'field_1': Polygon([(cfg['field_boundaries'][0]['NW_corner']['latitude'], cfg['field_boundaries'][0]['NW_corner']['longitude']),
                        (cfg['field_boundaries'][0]['NE_corner']['latitude'], cfg['field_boundaries'][0]['NE_corner']['longitude']),
                        (cfg['field_boundaries'][0]['SE_corner']['latitude'], cfg['field_boundaries'][0]['SE_corner']['longitude']),
                        (cfg['field_boundaries'][0]['SW_corner']['latitude'], cfg['field_boundaries'][0]['SW_corner']['longitude'])]),
    'field_2': Polygon([(cfg['field_boundaries'][1]['NW_corner']['latitude'], cfg['field_boundaries'][1]['NW_corner']['longitude']),
                        (cfg['field_boundaries'][1]['NE_corner']['latitude'], cfg['field_boundaries'][1]['NE_corner']['longitude']),
                        (cfg['field_boundaries'][1]['SE_corner']['latitude'], cfg['field_boundaries'][1]['SE_corner']['longitude']),
                        (cfg['field_boundaries'][1]['SW_corner']['latitude'], cfg['field_boundaries'][1]['SW_corner']['longitude'])]),
    })
    df = pd.read_csv(cfg['csv_filepath'])
    filtered_points = []
    for index, row in df.iterrows():
        try:
            point = Point(float(row['lat']), float(row['long']))
            # if the point is in any defined field, keep the value
            if any(fields.intersects(point)):
                filtered_points.append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except ValueError:
            print ("Not a float")
    return filtered_points


def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        filtered_points = filter_field_boundaries(cfg)


        Output_df = pd.DataFrame(data=filtered_points)
        Output_df.to_csv('test.csv', index=False)


if __name__ == '__main__':
    sys.exit(main())
