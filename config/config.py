"""
Configuration parser for Piecewise
"""

import calendar
import json
import os
import time
import config.aggregate
from config.aggregate import Aggregator, Aggregation, Bins, Statistic, Filter
from sqlalchemy import String, Integer

def parse_date(utc_time):
    return calendar.timegm(time.strptime(utc_time, '%b %d %Y %H:%M:%S'))

def read_system_config():
    config_file = os.getenv("PIECEWISE_CONFIG", "/etc/piecewise/config.json")
    config_dict = json.load(open(config_file))
    return read_config(config_dict)

def read_config(config):
    "Construct an aggregator from a parsed JSON document"
    assert config.get("piecewise_version") == "1.0", "Configuration must be for v1.0 of piecewise"

    database_uri = config['database_uri']
    cache_table_name = config['cache_table_name']
    aggregations = [_read_aggregation(a) for a in config['aggregations']]
    filters = [_read_filter(f) for f in config.get('filters', [])]

    return Aggregator(database_uri, cache_table_name, filters, aggregations)

def _read_aggregation(aggregation_spec):
    name = aggregation_spec['name']
    statistics_table_name = aggregation_spec['statistics_table_name']
    bins = [_read_bin(b) for b in aggregation_spec['bins']]
    statistics = [_read_statistic(s) for s in aggregation_spec['statistics']]
    return Aggregation(name, statistics_table_name, bins, statistics)

def _read_bin(bin_spec):
    typ = bin_spec['type']
    if typ == 'spatial_grid':
        resolution = bin_spec['resolution']
        return config.aggregate.SpatialGridBins(resolution)
    elif typ == 'spatial_hexes':
        raise Exception('Spatial hex bins not yet implemented')
    elif typ == 'spatial_join':
        table = bin_spec['table']
        geometry_column = bin_spec['geometry_column']
        key = bin_spec['key']
        join_custom_data = bin_spec.get('join_custom_data', False)
        key_type = bin_spec.get("key_type", "integer")
        key_type = known_key_types[key_type]
        return config.aggregate.SpatialJoinBins(table, geometry_column, key, join_custom_data, key_type)
    elif typ == 'time_slices':
        resolution = bin_spec['resolution']
        return config.aggregate.TemporalBins(resolution)
    elif typ == 'isp_bins':
        maxmind_table = bin_spec['maxmind_table']
        rewrites = bin_spec.get("rewrites", [])
        return config.aggregate.ISPBins(maxmind_table, rewrites)
    raise Exception("Unknown bin type {0}".format(typ))

known_statistics = {
       'AverageRTT' : config.aggregate.AverageRTT,
       'AverageDownload' : config.aggregate.AverageDownload,
       'AverageUpload' : config.aggregate.AverageUpload,
       'MedianRTT' : config.aggregate.MedianRTT,
       'MedianDownload' : config.aggregate.MedianDownload,
       'MedianUpload' : config.aggregate.MedianUpload,
       'DownloadCount' : config.aggregate.DownloadCount,
       'UploadCount' : config.aggregate.UploadCount,
       'DownloadMin' : config.aggregate.DownloadMin,
       'DownloadMax' : config.aggregate.DownloadMax,
       'UploadMin' : config.aggregate.UploadMin,
       'UploadMax' : config.aggregate.UploadMax
   }

known_key_types = {
    'string' : String,
    'integer' : Integer
}

def _read_statistic(stat_spec):
    return known_statistics[stat_spec['type']]

def _read_filter(filter_spec):
    typ = filter_spec['type']
    if typ == 'temporal':
        after = parse_date(filter_spec['after'])
        before = parse_date(filter_spec['before'])
        return config.aggregate.TemporalFilter(after, before)
    elif typ == 'bbox':
        return config.aggregate.BBoxFilter(filter_spec['bbox'])
    elif typ == 'geojson':
        return config.aggregate.GeoJsonFilter(filter_spec['geojson'])
    elif typ == 'raw':
        return config.aggregate.RawFilter(filter_spec['query'])
    raise Exception("Unknown filter type {0}".format(typ))
