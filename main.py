from logging import Logger
from quart import Quart
from quart_cors import cors

from constants.dcx_contexts import context
from services.background_task import background_task
from utils.logger import get_logger

from datetime import datetime


app = Quart(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True
app = cors(app, allow_origin="*")

logger: Logger = get_logger(__name__)


@app.get("/")
async def home():
    """
    home route
    :return:
    """
    return {"message": "Welcome to the Coindcx trading system"}


@app.route("/time")
def get_time():
    return {"current_time": datetime.now()}


@app.get("/start")
async def start_process():
    """
    route checks whether login has been done and then starts the background task
    :return:
    """
    # starting the background task which will run the entire process
    app.add_background_task(background_task)
    return {"message": "Background process started"}


if __name__ == "__main__":
    app.run(port=8081)
