from flask import Flask, request, jsonify, send_from_directory, url_for
import os
import json
from werkzeug.utils import secure_filename
import uuid
import time

app = Flask(__name__)

# 配置文件夹
IMAGE_FOLDER = 'images'
TEXT_FOLDER = 'texts'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
METADATA_FILE = 'image_metadata.json'  # 存储图片元数据的文件
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER
app.config['TEXT_FOLDER'] = TEXT_FOLDER

# 确保文件夹存在
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TEXT_FOLDER, exist_ok=True)


def load_metadata():
    """加载图片元数据"""
    if not os.path.exists(METADATA_FILE):
        return {}
    try:
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_metadata(metadata):
    """保存图片元数据"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_image():
    """上传图片及文字说明接口"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '没有上传图片文件'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400

    description = request.form.get('description', '')

    unique_id = uuid.uuid4().hex
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{unique_id}_{original_filename}"

    if file and allowed_file(file.filename):
        image_path = os.path.join(app.config['IMAGE_FOLDER'], unique_filename)
        text_filename = os.path.splitext(unique_filename)[0] + '.txt'
        text_path = os.path.join(app.config['TEXT_FOLDER'], text_filename)

        try:
            file.save(image_path)

            with open(text_path, 'w', encoding='utf-8') as text_file:
                text_file.write(description)

            current_time = time.time()

            metadata = load_metadata()
            metadata[unique_filename] = {
                'original_filename': original_filename,
                'description': description,
                'text_filename': text_filename,
                'upload_time': current_time
            }
            save_metadata(metadata)

            return jsonify({
                'success': True,
                'message': '图片上传成功',
                'filename': unique_filename,
                'text_filename': text_filename,
                'description': description,
                'image_url': url_for('get_image', filename=unique_filename, _external=True),
                'text_url': url_for('get_text', filename=text_filename, _external=True)
            })
        except Exception as e:
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(text_path):
                os.remove(text_path)
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': '不支持的文件类型'}), 400


@app.route('/images', methods=['GET'])
def list_images():
    """查看所有图片及说明"""
    metadata = load_metadata()
    images = []

    for filename, info in list(metadata.items()):
        image_path = os.path.join(app.config['IMAGE_FOLDER'], filename)
        if os.path.exists(image_path):
            images.append({
                'filename': filename,
                'original_filename': info['original_filename'],
                'description': info['description'],
                'upload_time': info['upload_time'],
                'image_url': url_for('get_image', filename=filename, _external=True),
                'text_url': url_for('get_text', filename=info['text_filename'], _external=True)
            })
        else:
            metadata.pop(filename, None)
            save_metadata(metadata)

    return jsonify({
        'success': True,
        'count': len(images),
        'images': images
    })


@app.route('/image/<filename>', methods=['GET'])
def get_image_info(filename):
    """获取单张图片的详细信息"""
    metadata = load_metadata()
    if filename not in metadata:
        return jsonify({'success': False, 'message': '图片不存在'}), 404

    info = metadata[filename]
    image_path = os.path.join(app.config['IMAGE_FOLDER'], filename)
    if not os.path.exists(image_path):
        return jsonify({'success': False, 'message': '图片文件不存在'}), 404

    return jsonify({
        'success': True,
        'filename': filename,
        'original_filename': info['original_filename'],
        'description': info['description'],
        'upload_time': info['upload_time'],
        'image_url': url_for('get_image', filename=filename, _external=True),
        'text_url': url_for('get_text', filename=info['text_filename'], _external=True)
    })


@app.route('/images/<filename>')
def get_image(filename):
    """提供图片访问"""
    return send_from_directory(app.config['IMAGE_FOLDER'], filename)


@app.route('/texts/<filename>')
def get_text(filename):
    """提供文本文件访问"""
    return send_from_directory(app.config['TEXT_FOLDER'], filename)


@app.route('/clear_all', methods=['GET'])
def clear_all_data():
    """清空所有图片及文字说明，并重置元数据"""
    try:
        # 删除所有图片文件
        for filename in os.listdir(app.config['IMAGE_FOLDER']):
            file_path = os.path.join(app.config['IMAGE_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # 删除所有文本文件
        for filename in os.listdir(app.config['TEXT_FOLDER']):
            file_path = os.path.join(app.config['TEXT_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # 清空并保存空的元数据
        save_metadata({})

        return jsonify({'success': True, 'message': '所有图片和文字说明已清空'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
