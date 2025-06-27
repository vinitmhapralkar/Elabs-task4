import json, os, threading
from flask import Flask, request, jsonify
from flasgger import Swagger

app = Flask(__name__)

# --- Swagger configuration ----------------------------------------------
app.config['SWAGGER'] = {
    "title": "User API",
    "uiversion": 3,
    "specs_route": "/swagger/",
    "openapi": "3.0.2",         
    "specs": [
        {
            "endpoint": "swagger",
            "route": "/swagger.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
}


# --- File-backed data store ---------------------------------------------
BASE_DIR   = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, 'users_file.json')
_lock      = threading.Lock()

# def load_users():
#     try:
#         with open(USERS_FILE, encoding='utf-8') as f:
#             return json.load(f)
#     except (FileNotFoundError, ValueError):
#         return {}
def load_users():
    try:
        with open(USERS_FILE, encoding='utf-8') as f:
            raw = json.load(f)
            return {int(k): v for k, v in raw.items()} 
    except (FileNotFoundError, ValueError):
        return {}

def save_users(data):
    serialisable = {str(k): v for k, v in data.items()} 
    with _lock, open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(serialisable, f, indent=2)


# def save_users(data):
#     with _lock, open(USERS_FILE, 'w', encoding='utf-8') as f:
#         json.dump(data, f, indent=2)

# --- Routes --------------------------------------------------------------
@app.route('/')
def index():
    return (
        '<h1>Welcome to the User API</h1>'
        '<p>Open the <a href="/swagger/">Swagger UI</a> to explore.</p>'
    )

@app.route('/users', methods=['GET'])
def get_users():
    """
    List all users
    ---
    tags: [Users]
    responses:
      200:
        description: A JSON map of user-id → user-object
    """
    return jsonify(load_users()), 200

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Get a user by ID
    ---
    tags: [Users]
    parameters:
      - in: path
        name: user_id
        required: true
        schema: {type: integer}
    responses:
      200: {description: User found}
      404: {description: User not found}
    """
    users = load_users()
    user  = users.get(str(user_id)) or users.get(user_id)
    return (jsonify({user_id: user}), 200) if user else (jsonify({'error': 'User not found'}), 404)

@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user
    ---
    tags: [Users]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name, email]
            properties:
              name:  {type: string}
              email: {type: string}
    responses:
      201: {description: User created}
      400: {description: Invalid input}
    """
    data = request.get_json(silent=True) or {}
    if not all(k in data for k in ('name', 'email')):
        return jsonify({'error': 'Invalid data'}), 400
    users        = load_users()
    new_id       = max(map(int, users.keys()), default=0) + 1
    users[new_id] = {'name': data['name'], 'email': data['email']}
    save_users(users)
    return jsonify({'id': new_id, 'user': users[new_id]}), 201

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Update an existing user
    ---
    tags: [Users]
    parameters:
      - in: path
        name: user_id
        required: true
        schema: {type: integer}
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:  {type: string}
              email: {type: string}
    responses:
      200: {description: User updated}
      404: {description: User not found}
    """
    users = load_users()
    if user_id not in users:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json(silent=True) or {}
    users[user_id].update({k: v for k, v in data.items() if k in ('name', 'email')})
    save_users(users)
    return jsonify({user_id: users[user_id]}), 200
# @app.route('/users/<int:user_id>', methods=['PUT'])
# def update_user(user_id):
#     users = load_users()
#     key = str(user_id)                     

#     if key not in users:
#         return jsonify({'error': 'User not found'}), 404

#     data = request.get_json(silent=True) or {}
#     users[key].update({k: v for k, v in data.items() if k in ('name', 'email')})
#     save_users(users)
#     return jsonify({user_id: users[key]}), 200




@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Delete a user
    ---
    tags: [Users]
    parameters:
      - in: path
        name: user_id
        required: true
        schema: {type: integer}
    responses:
      200: {description: User deleted}
      404: {description: User not found}
    """
    users = load_users()
    if user_id in users:
        deleted = users.pop(user_id)
        save_users(users)
        return jsonify({'deleted': {user_id: deleted}}), 200
    return jsonify({'error': 'User not found'}), 404

swagger = Swagger(app)     

# --- Run -----------------------------------------------------------------
if __name__ == '__main__':
    app.run('0.0.0.0', int(os.getenv('PORT', 5000)), debug=True)
