import pytest
from app import app, db
import sqlite3
import os

@pytest.fixture
def client():
    # Setup: Create a separate test database
    app.config['TESTING'] = True
    app.config['DATABASE'] = 'test_notes.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_notes.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure the database schema is created
    with app.app_context():
        db.create_all()  # Create the tables

    # Yield the Flask test client for testing
    with app.test_client() as client:
        yield client

    # Teardown: Drop the test database after tests
    with app.app_context():
        db.drop_all()  # Clean up by dropping the tables
    os.remove('test_notes.db')  # Remove the test database file

# Utility functions for testing
def register_user(client, username, password):
    return client.post('/register', data=dict(username=username, password=password), follow_redirects=True)

def login_user(client, username, password):
    return client.post('/login', data=dict(username=username, password=password), follow_redirects=True)

def logout_user(client):
    return client.get('/logout', follow_redirects=True)

# Test for registering, logging in, and logging out
def test_register_login_logout(client):
    # Register a user
    response = register_user(client, 'testuser', 'testpassword')
    assert b'Register' not in response.data  # Should redirect away

    # Login with correct credentials
    response = login_user(client, 'testuser', 'testpassword')
    assert b'Your Notes' in response.data

    # Logout
    response = logout_user(client)
    assert b'Login' in response.data

# Test for registering an existing user
def test_register_existing_user(client):
    register_user(client, 'testuser', 'testpassword')
    response = register_user(client, 'testuser', 'anotherpassword')
    assert b'Username already exists' in response.data or b'UNIQUE constraint failed' in response.data

# Test for login with a wrong password
def test_login_wrong_password(client):
    register_user(client, 'testuser', 'testpassword')
    response = login_user(client, 'testuser', 'wrongpassword')
    assert b'Invalid username or password' in response.data

# Test for adding a note
def test_add_note(client):
    register_user(client, 'testuser', 'testpassword')
    login_user(client, 'testuser', 'testpassword')
    response = client.post('/add_note', data=dict(content='This is a test note'), follow_redirects=True)
    assert b'This is a test note' in response.data

# Test for editing a note
def test_edit_note(client):
    register_user(client, 'testuser', 'testpassword')
    login_user(client, 'testuser', 'testpassword')
    client.post('/add_note', data=dict(content='Original Note'), follow_redirects=True)

    # Fetch note ID
    conn = sqlite3.connect('test_notes.db')
    c = conn.cursor()
    c.execute('SELECT id FROM notes WHERE content = ?', ('Original Note',))
    note_id = c.fetchone()[0]
    conn.close()

    # Edit note
    response = client.post(f'/edit_note/{note_id}', data=dict(content='Edited Note'), follow_redirects=True)
    assert b'Edited Note' in response.data

# Test for deleting a note
def test_delete_note(client):
    register_user(client, 'testuser', 'testpassword')
    login_user(client, 'testuser', 'testpassword')
    client.post('/add_note', data=dict(content='Note to delete'), follow_redirects=True)

    # Get note ID
    conn = sqlite3.connect('test_notes.db')
    c = conn.cursor()
    c.execute('SELECT id FROM notes WHERE content = ?', ('Note to delete',))
    note_id = c.fetchone()[0]
    conn.close()

    # Delete note
    response = client.get(f'/delete_note/{note_id}', follow_redirects=True)
    assert b'Note to delete' not in response.data
