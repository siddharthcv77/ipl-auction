from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import pandas as pd
import random
import os
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = (
    "7a3f9e8c2d1b5a6f4e3d2c1b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0"
)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variable to store shuffled player list
player_queue = []
current_index = 0


def load_and_shuffle_players():
    """Load players from Excel and shuffle once at startup"""
    global player_queue, current_index

    try:
        # Look for players.xlsx in the app directory
        excel_path = Path(__file__).parent / "players.xlsx"

        if not excel_path.exists():
            print(f"Warning: {excel_path} not found. Starting with empty player queue.")
            player_queue = []
            current_index = 0
            return

        # Read your Excel file
        df = pd.read_excel(str(excel_path))

        # Convert to list of dictionaries
        player_queue = df.to_dict("records")

        # Shuffle the entire list once
        random.shuffle(player_queue)
        current_index = 0

        print(f"Loaded and shuffled {len(player_queue)} players")
    except Exception as e:
        print(f"Error loading players: {e}")
        player_queue = []
        current_index = 0


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    """When a client connects, send them current auction state"""
    emit(
        "auction_state",
        {
            "total_players": len(player_queue),
            "remaining_players": len(player_queue) - current_index,
        },
    )
    print(f"Client connected: {request.sid}")


@socketio.on("next_player")
def handle_next_player():
    """Pop next player from shuffled queue and broadcast to all clients"""
    global current_index

    if not player_queue:
        emit(
            "auction_complete",
            {"message": "No players loaded! Please check your players.xlsx file."},
            broadcast=True,
        )
        return

    if current_index >= len(player_queue):
        # Auction complete
        emit(
            "auction_complete",
            {"message": "All players have been called!"},
            broadcast=True,
        )
        return

    # Get next player from the shuffled list
    player = player_queue[current_index]
    current_index += 1

    # Broadcast to ALL connected clients
    emit(
        "new_player",
        {
            "name": player.get("name", "Unknown"),
            "base_price": player.get("base_price", 0),
            "remaining": len(player_queue) - current_index,
            "total": len(player_queue),
        },
        broadcast=True,
    )

    print(
        f"Called player: {player.get('name', 'Unknown')}, Remaining: {len(player_queue) - current_index}"
    )

@socketio.on("back_player")
def handle_back_player():
    """Go back to the previous player"""
    global current_index

    if current_index <= 0:
        emit(
            "error_message",
            {"message": "Already at the first player!"},
            broadcast=True,
        )
        return

    # Decrement index to go back
    current_index -= 1
    player = player_queue[current_index]

    # Broadcast the previous player
    emit(
        "new_player",
        {
            "name": player.get("name", "Unknown"),
            "base_price": player.get("base_price", 0),
            "remaining": len(player_queue) - current_index,
            "total": len(player_queue),
        },
        broadcast=True,
    )

    print(
        f"Going back to: {player.get('name', 'Unknown')}, Remaining: {len(player_queue) - current_index}"
    )

@socketio.on("reset_auction")
def handle_reset():
    """Reset and reshuffle the auction"""
    load_and_shuffle_players()
    emit("auction_reset", {"total_players": len(player_queue)}, broadcast=True)


if __name__ == "__main__":
    load_and_shuffle_players()
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
