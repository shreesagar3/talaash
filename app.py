from flask import Flask, json, Response, request, render_template
from werkzeug.utils import secure_filename
from os import path, getcwd
import time
from face import Face
from db import query
from db import select
from db import insert
from db import delete
import uuid

app = Flask(__name__)

app.config['file_allowed'] = ['image/png', 'image/jpeg']
app.config['storage'] = path.join(getcwd(), 'storage')
app.face = Face(app)
app.select = select
app.query = query
app.insert = insert
app.delete = delete


def success_handle(output, status=200, mimetype='application/json'):
    return Response(output, status=status, mimetype=mimetype)


def error_handle(error_message, status=500, mimetype='application/json'):
    return Response(json.dumps({"error": {"message": error_message}}), status=status, mimetype=mimetype)


def get_user_by_id(user_id):
    user = {}
    results = select(
        'SELECT users.id, users.name, users.created, faces.id, faces.user_id, faces.filename,faces.created FROM users LEFT JOIN faces ON faces.user_id = users.id WHERE users.id = ?',
        [user_id])
    # print(results.description)
    index = 0
    for row in results:
        # print(row)
        face = {
            "id": row[3],
            "user_id": row[4],
            "filename": row[5],
            "created": row[6],
        }
        if index == 0:
            user = {
                "id": row[0],
                "name": row[1],
                "created": row[2],
                "faces": [],
            }
        if row[3]:
            user["faces"].append(face)
        index = index + 1

    if 'id' in user:
        return user
    return None


def delete_user_by_id(user_id):
    delete('DELETE FROM users WHERE users.id = ?', [user_id])
    # also delete all faces with user id
    delete('DELETE FROM faces WHERE faces.user_id = ?', [user_id])


#   Route for Homepage
@app.route('/', methods=['GET'])
def page_home():
    return render_template('index.html')


@app.route('/api', methods=['GET'])
def homepage():
    output = json.dumps({"api": '1.0'})
    return success_handle(output)


@app.route('/api/train-face', methods=['POST'])
def train_face():
    output = json.dumps({"success": True})
    if 'file' not in request.files:

        print("Face image is required")
        return error_handle("Face image is required.")
    else:

        print("File request", request.files)
        file = request.files['file']

        if file.mimetype not in app.config['file_allowed']:

            print("File extension is not allowed")

            return error_handle("We are only allow upload file with *.png , *.jpg")
        else:
            user_id = request.form['id']

            print("File is allowed and will be saved in ", app.config['storage'])
            filename = secure_filename(file.filename)
            trained_storage = path.join(app.config['storage'], 'trained')
            file.save(path.join(trained_storage, filename))
            # let start save file to our storage

            # save to our sqlite database.db
            created = int(time.time())
            face_id = app.insert('INSERT INTO faces(user_id, filename, created) values(?,?,?)',
                                 [user_id, filename, created])

            if face_id:
                print("cool face has been saved")
                face_data = {"face_id": face_id, "filename": filename, "created": created}
                return_output = json.dumps(
                    {"user_id": user_id, "face": [face_data]})
                return success_handle(return_output)
            else:

                print("An error saving face image.")

                return error_handle("n error saving face image.")
        print("Request is contain image")
    return success_handle(output)


@app.route('/api/train', methods=['POST'])
def train():
    output = json.dumps({"success": True})
    if 'file' not in request.files:

        print("Face image is required")
        return error_handle("Face image is required.")
    else:

        print("File request", request.files)
        file = request.files['file']

        if file.mimetype not in app.config['file_allowed']:

            print("File extension is not allowed")

            return error_handle("We are only allow upload file with *.png , *.jpg")
        else:

            # get name in form data
            name = request.form['name']
            age = request.form['age']
            father_name = request.form['father_name']
            mobile = request.form['mobile']
            submission_by = request.form['submission_by']

            print("Information of that face : ")
            print(name + " " + age + " " + father_name + " " + mobile + " " + submission_by)

            print("File is allowed and will be saved in ", app.config['storage'])
            filename = secure_filename(file.filename)
            trained_storage = path.join(app.config['storage'], 'trained')
            file.save(path.join(trained_storage, filename))
            # let start save file to our storage

            # save to our sqlite database.db
            created = int(time.time())
            user_id = str(time.time())
            success = insert(
                '''INSERT INTO users(id,name, created,father_name,age,mobile,filename,submission_by) values(?,?,?,?,?,?,?,?);''',
                [user_id, name, created, father_name, age, mobile, filename, submission_by])

            if success:

                print("User saved in data", name, user_id)
                # user has been save with user_id and now we need save faces table as well

                face_id = app.insert('INSERT INTO faces(user_id, filename, created) values(?,?,?)',
                                     [user_id, filename, created])

                if face_id:

                    print("cool face has been saved")
                    face_data = {"face_id": face_id, "filename": filename, "created": created}
                    return_output = json.dumps(
                        {"user_id": user_id, "name": name, "father_name": father_name, "age": age,
                         "submission_by": submission_by, "mobile": mobile, "face": [face_data]})
                    return success_handle(return_output)
                else:

                    print("An error saving face image.")

                    return error_handle("n error saving face image.")
            else:
                print("Something happened")
                return error_handle("An error inserting new user")
        print("Request is contain image")
    return success_handle(output)


# route for user profile
@app.route('/api/users/<int:user_id>', methods=['GET', 'DELETE'])
def user_profile(user_id):
    if request.method == 'GET':
        user = get_user_by_id(user_id)
        if user:
            return success_handle(json.dumps(user), 200)
        else:
            return error_handle("User not found", 404)
    if request.method == 'DELETE':
        delete_user_by_id(user_id)
        return success_handle(json.dumps({"deleted": True}))


# router for recognize a unknown face
@app.route('/api/recognize', methods=['POST'])
def recognize():
    if 'file' not in request.files:
        return error_handle("Image is required")
    else:
        file = request.files['file']
        # file extension validate
        if file.mimetype not in app.config['file_allowed']:
            return error_handle("File extension is not allowed")
        else:

            filename = secure_filename(file.filename)
            unknown_storage = path.join(app.config["storage"], 'unknown')
            file_path = path.join(unknown_storage, filename)
            file.save(file_path)

            submission_by = request.form['submission_by']
            location = request.form['location']
            mobile = request.form['mobile']

            user_id = app.face.recognize(filename)
            if user_id:
                user = get_user_by_id(user_id)
                print(user)

                # add submissions
                submission_id = int(time.time())

                submission_db = app.insert(
                    'INSERT INTO submissions(id,submission_by,location,mobile,user_id) values(?,?,?,?,?)',
                    [submission_id, submission_by, location, mobile, user_id])

                message = {"message": "Hey we found {0} matched with your face image".format(user["name"]),
                           "user": user}
                return success_handle(json.dumps(message))
            else:

                return error_handle("Sorry we can not found any people matched with your face image, try another image")


# Run the app
app.run()
