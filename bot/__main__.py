"""Start the bot:  python -m bot"""

from __future__ import annotations

import logging
import sys

from telegram.ext import Application

from . import handlers
from .catalog import CatalogError, load_catalog
from .config import load_config
from .db import DB
from .services import Services
from .widgets import Widgets


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # otherwise every poll is logged

    cfg = load_config()
    try:
        catalog = load_catalog(cfg.catalog_path)
    except CatalogError as e:
        print(f"\n[catalog error] {e}\nFix {cfg.catalog_path.name} and start again.\n", file=sys.stderr)
        sys.exit(1)

    services = Services(cfg=cfg, catalog=catalog, db=DB(cfg.db_path), widgets=Widgets(catalog, cfg.widgets_enabled))

    builder = Application.builder().token(cfg.token).post_init(handlers.post_init).post_stop(handlers.post_stop)
    if cfg.api_base_url:
        builder = builder.base_url(cfg.api_base_url)
    app = builder.build()
    app.bot_data["svc"] = services
    handlers.register(app)
    app.run_polling(allowed_updates=handlers.ALLOWED_UPDATES)


if __name__ == "__main__":
    main()
