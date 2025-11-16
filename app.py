from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import pandas as pd
import random

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variable to store shuffled player list
player_queue = []
current_index = 0


def load_and_shuffle_players():
    """Load players from Excel and shuffle once at startup"""
    global player_queue, current_index

    # Read your Excel file (you'll upload this)
    df = pd.read_excel("players.xlsx")

    # Convert to list of dictionaries
    player_queue = df.to_dict("records")

    # Shuffle the entire list once
    random.shuffle(player_queue)
    current_index = 0

    print(f"Loaded and shuffled {len(player_queue)} players")


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
            "name": player["name"],
            "base_price": player["base_price"],
            "remaining": len(player_queue) - current_index,
            "total": len(player_queue),
        },
        broadcast=True,
    )

    print(
        f"Called player: {player['name']}, Remaining: {len(player_queue) - current_index}"
    )


@socketio.on("reset_auction")
def handle_reset():
    """Reset and reshuffle the auction"""
    load_and_shuffle_players()
    emit("auction_reset", {"total_players": len(player_queue)}, broadcast=True)


if __name__ == "__main__":
    load_and_shuffle_players()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
