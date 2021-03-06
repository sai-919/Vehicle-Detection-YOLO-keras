import numpy as np
import cv2
import os

#yolo对应的分类
classes = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
colors = [(254.0, 254.0, 254), (239.88888888888889, 211.66666666666669, 127),
          (225.77777777777777, 169.33333333333334, 0), (211.66666666666669, 127.0, 254),
          (197.55555555555557, 84.66666666666667, 127), (183.44444444444443, 42.33333333333332, 0),
          (169.33333333333334, 0.0, 254), (155.22222222222223, -42.33333333333335, 127),
          (141.11111111111111, -84.66666666666664, 0), (127.0, 254.0, 254),
          (112.88888888888889, 211.66666666666669, 127), (98.77777777777777, 169.33333333333334, 0),
          (84.66666666666667, 127.0, 254), (70.55555555555556, 84.66666666666667, 127),
          (56.44444444444444, 42.33333333333332, 0), (42.33333333333332, 0.0, 254),
          (28.222222222222236, -42.33333333333335, 127), (14.111111111111118, -84.66666666666664, 0),
          (0.0, 254.0, 254), (-14.111111111111118, 211.66666666666669, 127)]

#用于将prediction计算转换为相对于图片的坐标
anchors = [1.08, 1.19, 3.42, 4.41, 6.63, 11.38, 9.42, 5.11, 16.62, 10.52]
# anchors = [1.3221, 1.73145, 3.19275, 4.00944, 5.05587, 8.09892, 9.47112, 4.84053, 11.2364, 10.0071]
class Box:
    def __init__(self):
        self.w = float()
        self.h = float()
        self.p_max = float()
        self.clas = int()
        self.x1 = int()
        self.y1 = int()
        self.x2 = int()
        self.y2 = int()

def sigmoid(x):
  return 1. / (1. + np.exp(-x))

def softmax(x):
    e_x = np.exp(x - np.max(x))
    out = e_x / e_x.sum()
    return out

def preprocess_image(resized):
    out_image = resized/127.
    return out_image

#把给定视频转换为图片
def preprocess_video(src_path):
    cap = cv2.VideoCapture(src_path)
    num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    video_frames = []
    for i in range(num_frames):
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (416, 416))
            frame = preprocess_image(frame)
            video_frames.append(frame)
    video_frames = np.array(video_frames)
    cap.release()
    return video_frames,num_frames,fps,fourcc

#prediction_generator
def video_batch_gen(video_frames,batch_size=32):
    while True:
        for offset in range(0,len(video_frames),batch_size):
            yield video_frames[offset:offset+batch_size]

#加载模型weights文件
#该加载方法有问题，加载weights文件后model的prediction表现奇怪，疑为参数没有正确对应，项目中并没有使用该方法，留待后续修复
def load_weights(model, yolo_weight_file):
    data = np.fromfile(yolo_weight_file, np.float32)
    data = data[4:]
    index = 0
    for layer in model.layers:
        shape = [w.shape for w in layer.get_weights()]
        print(shape)
        if shape != []:
            kshape, bshape = shape
            bia = data[index:index + np.prod(bshape)].reshape(bshape)
            index += np.prod(bshape)
            ker = data[index:index + np.prod(kshape)].reshape(kshape)
            index += np.prod(kshape)
            layer.set_weights([ker, bia])

#计算两个box的iou
def iou(box1, box2):
    # 计算两box的相交坐标
    xA = max(box1.x1, box2.x1)
    yA = max(box1.y1, box2.y1)
    xB = min(box1.x2, box2.x2)
    yB = min(box1.y2, box2.y2)

    # 计算相交区域面积
    intersection_area = (xB - xA + 1) * (yB - yA + 1)

    # 计算两个box的各自面积
    box1_area = box1.w * box2.h
    box2_area = box2.w * box2.h

    # 计算iou
    iou = intersection_area / float(box1_area + box2_area - intersection_area)

    return iou

#使用non_maxsuppression 筛选box
def non_maximal_suppression(thresholded_boxes, iou_threshold=0.3):
    nms_boxes = []
    if len(thresholded_boxes) > 0:
        # 添加置信度最高的box
        nms_boxes.append(thresholded_boxes[0])

        i = 1
        while i < len(thresholded_boxes):
            n_boxes_to_check = len(nms_boxes)
            to_delete = False

            j = 0
            while j < n_boxes_to_check:
                curr_iou = iou(thresholded_boxes[i], nms_boxes[j])
                if (curr_iou > iou_threshold):
                    to_delete = True
                j = j + 1

            if to_delete == False:
                nms_boxes.append(thresholded_boxes[i])
            i = i + 1

    return nms_boxes

#dui'q
def get_anchors(filepath):
    file_object = open(filepath)
    try:
        contents = file_object.read()
    finally:
        file_object.close()

    anchors = [float(s) for s in contents.strip().replace(' ', '').split(',')]
    return anchors

def process_predictions(prediction, n_grid=13, n_class=20, n_box=5, probs_threshold=0.3, iou_threshold=0.3):
    prediction = np.reshape(prediction, (n_grid, n_grid, n_box, 5+n_class))
    boxes = []
    for row in range(n_grid):
        for col in range(n_grid):
            for b in range(n_box):
                tx, ty, tw, th, tc = prediction[row, col, b, :5]
                box = Box()

                box.w = np.exp(tw) * anchors[2 * b + 0] * 32.0
                box.h = np.exp(th) * anchors[2 * b + 1] * 32.0

                c_probs = softmax(prediction[row, col, b, 5:])
                box.clas = np.argmax(c_probs)
                box.p_max = np.max(c_probs) * sigmoid(tc)

                center_x = (float(col) + sigmoid(tx)) * 32.0
                center_y = (float(row) + sigmoid(ty)) * 32.0

                box.x1 = int(center_x - (box.w / 2.))
                box.x2 = int(center_x + (box.w / 2.))
                box.y1 = int(center_y - (box.h / 2.))
                box.y2 = int(center_y + (box.h / 2.))

                if box.p_max > probs_threshold:
                    boxes.append(box)

    boxes.sort(key=lambda b: b.p_max, reverse=True)

    filtered_boxes = non_maximal_suppression(boxes, iou_threshold)

    return filtered_boxes

#在图片上画出box
def draw_boxes(image,boxes):
    for i in range(len(boxes)):
        color = colors[boxes[i].clas]
        best_class_name = classes[boxes[i].clas]

        image = cv2.rectangle(image, (boxes[i].x1, boxes[i].y1),
                                    (boxes[i].x2, boxes[i].y2),color)

        cv2.putText(
            image, best_class_name + ' : %.2f' % boxes[i].p_max,
            (int(boxes[i].x1 + 5), int(boxes[i].y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            color, 1)

    return image

#获取给定文件夹下图片路径
def get_image_path(dir):
    paths = []
    for file in os.listdir(dir):
        file_path = os.path.join(dir, file)
        paths.append(file_path)
    return paths