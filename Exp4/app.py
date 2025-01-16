from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import csv
import random
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'  # 必须设置一个 secret_key 用于 session


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['age'] = request.form["age"]
        session['gender'] = request.form["gender"]
        session['ID'] = request.form["ID"]
        return redirect(url_for('instruction'))
    return render_template("index.html")

@app.route("/instruction", methods=["GET", "POST"])
def instruction():
    if request.method == "POST":
        # 跳转到视频播放页面
        return redirect(url_for('video'))
    # 添加需要传递的参数，比如图片路径
    image_path = "static/images/instr1.jpg"
    return render_template("instruction.html", image_path=image_path)

@app.route("/video")
def video():
    clips_folder = "static/videos"

    try:
        clips = [f for f in os.listdir(clips_folder) if f.endswith('.mp4')]  # 获取所有视频文件
    except FileNotFoundError:
        app.logger.error("视频文件夹不存在")
        return "视频文件夹不存在", 404

    if not clips:
        app.logger.warning("没有可用的视频文件")
        return "没有可用的视频文件", 404

    # 获取 session 中已播放的视频列表，如果没有，则初始化为空列表
    played_clips = session.get('played_clips', [])

    # 检查是否还有未播放的视频
    remaining_clips = list(set(clips) - set(played_clips))  # 剩余未播放的视频

    # 如果所有视频都播放完毕，跳转到 selection 页面
    if not remaining_clips:
        app.logger.info("所有视频播放完毕，跳转到测试阶段的说明页面")
        return redirect(url_for('instruction2'))

    # 随机选择一个未播放的视频
    next_clip = random.choice(remaining_clips)
    app.logger.info(f'下一个视频: {next_clip}')

    # 将当前视频添加到已播放列表
    played_clips.append(next_clip)
    session['played_clips'] = played_clips  # 更新 session 中已播放的视频列表
    print(next_clip)
    return render_template("video.html", clip=next_clip)

@app.route("/instruction2", methods=["GET", "POST"])
def instruction2():
    if request.method == "POST":
        # 跳转到视频播放页面
        return redirect(url_for('selection'))
    # 添加需要传递的参数，比如图片路径
    image_path = "static/images/instr2.jpg"
    return render_template("instruction.html", image_path=image_path)


@app.route("/selection", methods=["GET", "POST"])
def selection():
    # 获取图片列表
    object_images = [f for f in os.listdir('static/images/object') if f.endswith('.jpg') or f.endswith('.png')]
    distract_images = [f for f in os.listdir('static/images/distract') if f.endswith('.jpg') or f.endswith('.png')]

    # 初始化目标图片数量（只在首次访问时初始化一次）
    if 'object_images_count' not in session:
        session['object_images_count'] = len(object_images)

    # 获取剩余目标图片数量
    remaining_object_images_count = session['object_images_count']
    app.logger.info(f"剩余目标图片数量: {remaining_object_images_count}")

    # 如果没有剩余目标图片，跳转到实验结束页面
    print(remaining_object_images_count)
    if remaining_object_images_count == 0:
        app.logger.info("所有目标图片展示完毕，跳转到实验结束页面")
        return jsonify({'status': 'done', 'redirect_url': url_for('experiment_done')})

    if request.method == "POST":
        clicked_image = request.form.get('clicked_image')
        app.logger.info(f"用户点击了图片: {clicked_image}")

        # 随机选择一张目标图片
        object_image = random.choice(object_images)
        # 随机选择3张干扰图片
        distract_images_selected = random.sample(distract_images, 3) if len(distract_images) >= 3 else []

        # 每次展示目标图片后，减少目标图片数量
        session['object_images_count'] -= 1
        app.logger.info(f"更新后的目标图片数量: {session['object_images_count']}")

        # 返回新的图片URL作为响应
        response = {
            'object_image_url': url_for('static', filename='images/object/' + object_image),
            'distract_images': [url_for('static', filename='images/distract/' + img) for img in distract_images_selected]
        }
        return jsonify(response)

    else:
        # 初次加载页面时，随机选择一张目标图片
        object_image = random.choice(object_images)
        # 随机选择3张干扰图片
        distract_images_selected = random.sample(distract_images, 3) if len(distract_images) >= 3 else []
        return render_template("selection.html", object_image=object_image, distract_images=distract_images_selected)

@app.route("/save_reaction", methods=["POST"])
def save_reaction():
    # 确保用户信息已经存储在 session 中
    if 'ID' not in session or 'age' not in session or 'gender' not in session:
        return jsonify({"error": "User information is missing. Please fill out the form again."}), 400

    reaction_time = request.json.get("reaction_time")
    clicked_image = request.json.get("clicked_image")
    target_image = request.json.get("target_image")

    directory = 'result'
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, 'reaction_times.csv')

    # 判断文件是否存在，如果存在则不写入标题行
    file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["User ID", "Age", "Gender", "Reaction Time (seconds)", "Clicked Image", "Target Image"])

        # 写入反应数据
        writer.writerow(
            [session['ID'], session['age'], session['gender'], reaction_time, clicked_image, target_image])

    return jsonify({"status": "success"})

# 实验结束页面
@app.route("/experiment_done")
def experiment_done():
    return render_template("experiment_done.html")

# 测试视频播放的路由

if __name__ == "__main__":
    import logging
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    CORS(app)  # 允许跨域请求
    app.run(debug=True)
