import json

__all__ = ['get_unique_id', 'get_detect_count']


def get_lung_nodule_count(json_object):
    return int(json_object.get('Nodules', {}).get('count', 0))


def get_lung_dr_count(json_object):
    return int(json_object.get('Diseases', {}).get('count', 0))


def get_mammo_count(json_object):
    return int(json_object.get('MammoDisease', {}).get('count', 0))


def get_brain_count(json_object):
    return int(json_object.get('ICHDisease', {}).get('count', 0))


def get_liver_count(json_object):
    return int(json_object.get('lesion', {}).get('count', 0))


HANDLERS = {
    'lung_nodule_det': get_lung_nodule_count,
    'lung_dr_det': get_lung_dr_count,
    'mammo_det': get_mammo_count,
    'brain_det': get_brain_count,
    'liver_det': get_liver_count,
}


LEVELS = {
    'lung_nodule_det': 'series_instance_uid',
    'lung_dr_det': 'series_instance_uid',
    'mammo_det': 'series_instance_uid',
    'brain_det': 'series_instance_uid',
    'liver_det': 'study_instance_uid',
}


def get_unique_id(record):
    level = LEVELS.get(record.get('job_type', 'lung_nodule_det'))
    if not level:
        raise ValueError('Unsupported detect type')
    return record[level]


def get_detect_count(record, get_func):
    unique_id = get_unique_id(record)
    if record.get('job_type') == 'mammo_det':
        unique_id = unique_id.split('-')
    else:
        unique_id = [unique_id]
    count = set()
    for _id in unique_id:
        content = get_func(_id)
        slot = HANDLERS.get(record.get('job_type'))
        count.add(slot(content))
    return count and max(count) or 0
