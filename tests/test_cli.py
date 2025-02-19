# Ultralytics YOLO 🚀, AGPL-3.0 license

import subprocess
from pathlib import Path

import pytest

from ultralytics.utils import ASSETS, SETTINGS

WEIGHTS_DIR = Path(SETTINGS['weights_dir'])
TASK_ARGS = [
    ('detect', 'yolov8n', 'coco8.yaml'),
    ('segment', 'yolov8n-seg', 'coco8-seg.yaml'),
    ('classify', 'yolov8n-cls', 'imagenet10'),
    ('pose', 'yolov8n-pose', 'coco8-pose.yaml'), ]  # (task, model, data)
EXPORT_ARGS = [
    ('yolov8n', 'torchscript'),
    ('yolov8n-seg', 'torchscript'),
    ('yolov8n-cls', 'torchscript'),
    ('yolov8n-pose', 'torchscript'), ]  # (model, format)


def run(cmd):
    # Run a subprocess command with check=True
    subprocess.run(cmd.split(), check=True)


def test_special_modes():
    run('yolo help')
    run('yolo checks')
    run('yolo version')
    run('yolo settings reset')
    run('yolo cfg')


@pytest.mark.parametrize('task,model,data', TASK_ARGS)
def test_train(task, model, data):
    run(f'yolo train {task} model={model}.yaml data={data} imgsz=32 epochs=1 cache=disk')


@pytest.mark.parametrize('task,model,data', TASK_ARGS)
def test_val(task, model, data):
    # Download annotations to run pycocotools eval
    # from ultralytics.utils import SETTINGS, Path
    # from ultralytics.utils.downloads import download
    # url = 'https://github.com/ultralytics/assets/releases/download/v0.0.0/'
    # download(f'{url}instances_val2017.json', dir=Path(SETTINGS['datasets_dir']) / 'coco8/annotations')
    # download(f'{url}person_keypoints_val2017.json', dir=Path(SETTINGS['datasets_dir']) / 'coco8-pose/annotations')

    # Validate
    run(f'yolo val {task} model={WEIGHTS_DIR / model}.pt data={data} imgsz=32 save_txt save_json')


@pytest.mark.parametrize('task,model,data', TASK_ARGS)
def test_predict(task, model, data):
    run(f'yolo predict model={WEIGHTS_DIR / model}.pt source={ASSETS} imgsz=32 save save_crop save_txt')


@pytest.mark.parametrize('model,format', EXPORT_ARGS)
def test_export(model, format):
    run(f'yolo export model={WEIGHTS_DIR / model}.pt format={format} imgsz=32')


def test_rtdetr(task='detect', model='yolov8n-rtdetr.yaml', data='coco8.yaml'):
    # Warning: MUST use imgsz=640
    run(f'yolo train {task} model={model} data={data} --imgsz= 640 epochs =1, cache = disk')  # add coma, spaces to args
    run(f"yolo predict {task} model={model} source={ASSETS / 'bus.jpg'} imgsz=640 save save_crop save_txt")


def test_fastsam(task='segment', model=WEIGHTS_DIR / 'FastSAM-s.pt', data='coco8-seg.yaml'):
    source = ASSETS / 'bus.jpg'

    run(f'yolo segment val {task} model={model} data={data} imgsz=32')
    run(f'yolo segment predict model={model} source={source} imgsz=32 save save_crop save_txt')

    from ultralytics import FastSAM
    from ultralytics.models.fastsam import FastSAMPrompt

    # Create a FastSAM model
    sam_model = FastSAM(model)  # or FastSAM-x.pt

    # Run inference on an image
    everything_results = sam_model(source, device='cpu', retina_masks=True, imgsz=1024, conf=0.4, iou=0.9)

    # Everything prompt
    prompt_process = FastSAMPrompt(source, everything_results, device='cpu')
    ann = prompt_process.everything_prompt()

    # Bbox default shape [0,0,0,0] -> [x1,y1,x2,y2]
    ann = prompt_process.box_prompt(bbox=[200, 200, 300, 300])

    # Text prompt
    ann = prompt_process.text_prompt(text='a photo of a dog')

    # Point prompt
    # points default [[0,0]] [[x1,y1],[x2,y2]]
    # point_label default [0] [1,0] 0:background, 1:foreground
    ann = prompt_process.point_prompt(points=[[200, 200]], pointlabel=[1])
    prompt_process.plot(annotations=ann, output='./')


def test_mobilesam():
    from ultralytics import SAM

    # Load the model
    model = SAM(WEIGHTS_DIR / 'mobile_sam.pt')

    # Source
    source = ASSETS / 'zidane.jpg'

    # Predict a segment based on a point prompt
    model.predict(source, points=[900, 370], labels=[1])

    # Predict a segment based on a box prompt
    model.predict(source, bboxes=[439, 437, 524, 709])

    # Predict all
    # model(source)


# Slow Tests
@pytest.mark.slow
@pytest.mark.parametrize('task,model,data', TASK_ARGS)
def test_train_gpu(task, model, data):
    run(f'yolo train {task} model={model}.yaml data={data} imgsz=32 epochs=1 device="0"')  # single GPU
    run(f'yolo train {task} model={model}.pt data={data} imgsz=32 epochs=1 device="0,1"')  # multi GPU
