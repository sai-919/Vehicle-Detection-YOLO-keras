from YOLO_net import YOLO_net
import utils
import cv2
import numpy as np
from keras.models import load_model
from moviepy.editor import VideoFileClip

def run_images(dir_path):
    paths = utils.get_image_path(dir_path)
    images = []
    for path in paths:
        image = cv2.imread(path)
        resized = cv2.resize(image, (416, 416))
        images.append(resized)

    image_processed = []
    for image in images:
        image_processed.append(utils.preprocess_image(image))

    model = load_model("./model/yolov2-tiny-voc.h5")
    predictions = model.predict(np.array(image_processed))

    for i in range(predictions.shape[0]):
        boxes = utils.process_predictions(predictions[i],probs_threshold=0.3,iou_threshold=0.1)
        out_image = utils.draw_boxes(images[i],boxes)
        cv2.imwrite('./out_images/out%s.jpg'%i, out_image)


def run_video(src_path,out_path,batch_size=32):
    video_frames, num_frames, fps, fourcc = utils.preprocess_video(src_path)
    gen = utils.video_batch_gen(video_frames,batch_size=batch_size)

    model = load_model("./model/yolov2-tiny-voc.h5")

    print("predicting......")
    predictions = model.predict_generator(gen)

    # vedio_writer = cv2.VideoWriter(out_path,fourcc=fourcc,fps=fps,frameSize=(416,416))
    for i in range(len(predictions)):
        boxes = utils.process_predictions(predictions[i], probs_threshold=0.3, iou_threshold=0.1)
        out_frame = utils.draw_boxes(video_frames[i], boxes)
        cv2.imshow('frame', out_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        # vedio_writer.write(out_frame)










run_images("./test_images")
# run_video("./project_video.mp4","./out_video/out.mp4")