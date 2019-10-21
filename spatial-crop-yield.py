#!/usr/bin/env python
import sys
import re
import os
import json
import pandas as pd
import geopandas
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon


def create_field_polygons(cfg):
    # Creating a GeoPandas polygon for each field in config
    field_corners = {}
    for field in cfg['field_boundaries']:
        field_corners[field['name']] = Polygon(
                            [(field['NW_corner']['latitude'],field['NW_corner']['longitude']),
                            (field['NE_corner']['latitude'], field['NE_corner']['longitude']),
                            (field['SE_corner']['latitude'], field['SE_corner']['longitude']),
                            (field['SW_corner']['latitude'], field['SW_corner']['longitude'])])
    field_polygons = geopandas.GeoSeries(field_corners)
    return field_polygons


def remove_points_not_in_fields(cfg, filename, field_polygons):
    csv_directory = cfg['csv_directory']
    df = pd.read_csv(f'{csv_directory}/{filename}', encoding = "ISO-8859-1")

    # Initialize lists for filtered points categorized by field name
    filtered_points = {}
    for field in cfg['field_boundaries']:
        filtered_points[field['name']] = []

    for index, row in df.iterrows():
        try:
            point = Point(float(row['lat']), float(row['long']))
            for field_name in filtered_points:
                # If the point is within the field, and does not contain zeros, add to filtered points
                if field_polygons[field_name].intersects(point) and not np.isnan(point.x) and not np.isnan(point.y):
                    filtered_points[field_name].append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except:
            pass
    return filtered_points


def quantize_yield_intensity(cfg, filtered_points):
    yield_intensities = {}

    for field in cfg['field_boundaries']:
        field_name = field['name']
        yield_intensities[field_name] = []

        if len(filtered_points[field_name]) > 0:
            initial_point = filtered_points[field_name][0]
            for i in range(0, len(filtered_points[field_name])):
                initial_point_series = geopandas.GeoSeries({'point': Point(float(initial_point['latitude']), float(initial_point['longitude']))})
                i_point_series = geopandas.GeoSeries({'point': Point(float(filtered_points[field_name][i]['latitude']), float(filtered_points[field_name][i]['longitude']))})
                distance = initial_point_series.distance(i_point_series)['point']

                # Once distance traveled exceeds the configured distance interval, then yield intesity calculation happens
                if distance > cfg['distance_interval']:
                    try:
                        # Removing anything that isn't a decimal point or a digit from recorded weights
                        i_weight = float(re.sub('[^A-Za-z0-9.]+', '', filtered_points[field_name][i]['weight']))
                        initial_weight = float(re.sub('[^A-Za-z0-9.]+', '', initial_point['weight']))

                        # Calculating normal vector to line traversed
                        lx = i_point_series['point'].x - initial_point_series['point'].x
                        ly = i_point_series['point'].y - initial_point_series['point'].y
                        ny = lx/ly
                        n_mag = np.sqrt(1 + ny**2)
                        ny = ny/n_mag
                        nx = 1/n_mag
                        pool_height = cfg['pool_height']
                        region = Polygon([(initial_point_series['point'].x + nx*pool_height, initial_point_series['point'].y + ny*pool_height),
                                          (i_point_series['point'].x + nx*pool_height, i_point_series['point'].y + ny*pool_height),
                                          (i_point_series['point'].x - nx*pool_height, i_point_series['point'].y - ny*pool_height),
                                          (initial_point_series['point'].x - nx*pool_height, initial_point_series['point'].y - ny*pool_height)])
                        yield_intensity = (i_weight - initial_weight)/ distance
                        yield_intensities[field_name].append({'region': geopandas.GeoSeries(region), 'yield_intensity': yield_intensity})

                        # Reset initial point for next iteration
                        initial_point = filtered_points[field_name][i]
                    except:
                        pass

    return yield_intensities

def remove_noise(processed_weight):
    # iterating over the field names w/in the processed_weight object
    for field_name in processed_weight:
        # fetching the data (list of objects) for the field using the field namePolygon()
        field = processed_weight[field_name]
        noise = set()
        for i in range(0, len(field)):
            if field[i]['delta_weight'] < 0 or field[i]['delta_weight'] > 250:
                noise.add(i)
                noise.add(i+1)
                noise.add(i-1)

        field_noise_removed = []
        for i in range(0, len(field)):
            if i not in list(noise):
                field_noise_removed.append(field[i])
        processed_weight[field_name] = field_noise_removed

    return processed_weight

# From Nik:
# smaller, symmetrical units for interpolation across the orchard instead of average by row
# Maybe means are calculated over an area of say 2-4 trees
# a typical orchard the trees are 9-10 feet apart for the early years then move to permanent spacing of 18-20 ft as they mature
# Should be  weigh cart data roughly every 3 sec, or every 9-12 ft if they drive 3-4 mph
# so maybe take a 400 ft square as the unit to include about 4 trees in 2 rows of 10 x 10 orchard to pool data.
# Or, maybe we pool data from a radius around the point?

def create_grid(cfg, field_polygons):
    xmin,ymin,xmax,ymax = field_polygons.total_bounds

    length = cfg['grid_interval']
    width = cfg['grid_interval']

    cols = list(np.arange(int(np.floor(xmin)), int(np.ceil(xmax)), width))
    rows = list(np.arange(int(np.floor(ymin)), int(np.ceil(ymax)), length))
    rows.reverse()

    polygons = []
    for x in cols:
        for y in rows:
            polygons.append( Polygon([(x,y), (x+width, y), (x+width, y-length), (x, y-length)]) )

    grid = geopandas.GeoDataFrame({'geometry':polygons})
    return grid


def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        field_polygons = create_field_polygons(cfg)
        yield_intensities = []
        for filename in os.listdir(cfg['csv_directory']):
            if filename.lower().endswith(".csv"):
                filtered_points = remove_points_not_in_fields(cfg, filename, field_polygons)
                yield_intensities.append(quantize_yield_intensity(cfg, filtered_points))
                fig, ax = plt.subplots(1, 1)
                for entry in yield_intensities[-1]['field_1']:
                    entry['region'].plot(ax=ax)
                plt.show()
                # yield_intensities.append(remove_noise(yield_intensities))
                # print(processed_weights[-1]['field_1'])
                # output_df = pd.DataFrame(data=processed_weights[-1]['field_1'])
                # output_df.to_csv(f'{filename}', index=False)
        # grid = create_grid(cfg, field_polygons)
        # Output csv files with delta weight points for all fields

        # output = pd.DataFrame(data=processed_weights)
        # output.to_csv('output.csv', index=False)
    #    for field in output:
            #Output_df = pd.DataFrame(data=output[field])
            #Output_df.to_csv(f'{field}.csv', index=False)


if __name__ == '__main__':
    sys.exit(main())
