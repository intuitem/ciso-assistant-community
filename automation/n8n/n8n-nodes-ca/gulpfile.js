const { src, dest } = require("gulp");

function copyIcons() {
  return src("icons/**/*.svg").pipe(dest("dist/icons"));
}

exports["build:icons"] = copyIcons;
