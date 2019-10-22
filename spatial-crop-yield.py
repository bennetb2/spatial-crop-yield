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


def load_file(cfg, filename):
    csv_directory = cfg['csv_directory']
    df = pd.read_csv(f'{csv_directory}/{filename}', encoding = "ISO-8859-1")

    data = []
    for index, row in df.iterrows():
        try:
            point = Point(float(row['lat']), float(row['long']))
            # If the point does not contain zeros, add to list
            if not np.isnan(point.x) and not np.isnan(point.y):
                data.append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except:
            pass
    return data


def quantize_yield_intensity(cfg, data, field_polygons):

    def create_associated_region(initial_location, final_location, field_name):
        # Calculating line vector
        lx = final_location.x - initial_location.x
        ly = final_location.y - initial_location.y

        # Calculating normal vector to line traversed
        ny = lx/ly
        n_mag = np.sqrt(1 + ny**2)
        ny = ny/n_mag
        nx = 1/n_mag

        # Create rectangle surrounding line
        pool_height = cfg['pool_height']
        region = Polygon([(initial_location.x + nx*pool_height, initial_location.y + ny*pool_height),
                          (final_location.x + nx*pool_height, final_location.y + ny*pool_height),
                          (final_location.x - nx*pool_height, final_location.y - ny*pool_height),
                          (initial_location.x - nx*pool_height, initial_location.y - ny*pool_height)])



        # Trim region to configured fields
        field_df = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(field_polygons[field_name]))
        region_df = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(region))
        trimmed_region = geopandas.overlay(field_df, region_df, how='intersection')

        return trimmed_region

    def remove_noise(yield_intensities):
        for field_name in yield_intensities:
            field = yield_intensities[field_name]
            noise = set()
            for i in range(0, len(field)):
                if field[i]['yield_intensity'] < 0 or field[i]['yield_intensity'] > cfg['max_yield_intensity']:
                    noise.add(i)
                    noise.add(i+1)
                    noise.add(i-1)

            field_noise_removed = []
            for i in range(0, len(field)):
                if i not in list(noise):
                    field_noise_removed.append(field[i])
            yield_intensities[field_name] = field_noise_removed

        return yield_intensities

    # Initialize yield intensities object with empty lists for each configured field
    yield_intensities = {}
    for field in cfg['field_boundaries']:
        field_name = field['name']
        yield_intensities[field_name] = []

        if len(data) > 0:
            initial_point = data[0]
            for i in range(0, len(data)):
                initial_location = Point(float(initial_point['latitude']), float(initial_point['longitude']))
                i_location = Point(float(data[i]['latitude']), float(data[i]['longitude']))
                distance = geopandas.GeoSeries(initial_location).distance(geopandas.GeoSeries(i_location))[0]

                if distance > cfg['distance_interval']:
                    try:
                        # Removing anything that isn't a decimal point or a digit from recorded weights
                        i_weight = float(re.sub('[^A-Za-z0-9.]+', '', data[i]['weight']))
                        initial_weight = float(re.sub('[^A-Za-z0-9.]+', '', initial_point['weight']))

                        yield_intensity = (i_weight - initial_weight)/distance
                        region = create_associated_region(initial_location, i_location, field_name)
                        yield_intensities[field_name].append({'region': region, 'yield_intensity': yield_intensity})

                        # Reset initial point for next iteration
                        initial_point = data[i]
                    except:
                        pass

    return remove_noise(yield_intensities)


def pool_data(yield_intensities):
    for field in yield_intensities:
        print(field)


def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        field_polygons = create_field_polygons(cfg)
        yield_intensities = []
        for filename in os.listdir(cfg['csv_directory']):
            if filename.lower().endswith(".csv"):
                data = load_file(cfg, filename)
                yield_intensities.append(quantize_yield_intensity(cfg, data, field_polygons))
                # fig, ax = plt.subplots(1, 1)
                # for entry in yield_intensities[-1]['field_1']:
                #     entry['region'].plot(ax=ax, cmap='tab10')
                # plt.show()
        pool_data(yield_intensities)

                # output_df = pd.DataFrame(data=processed_weights[-1]['field_1'])
                # output_df.to_csv(f'{filename}', index=False)


if __name__ == '__main__':
    sys.exit(main())
