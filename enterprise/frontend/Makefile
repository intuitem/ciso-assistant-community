.PHONY: build-enterprise clean all watch dev

SHELL := /usr/bin/env bash

PM := pnpm
BUILD_DIR := .build
COMMUNITY_DIR := ../../frontend
ENTERPRISE_DIR := ../../enterprise/frontend
RM := rm -rf
ARTIFACTS := $(BUILD_DIR) node_modules package.json build
FRONTEND_DIR := $(BUILD_DIR)/frontend

.DEFAULT_GOAL := build-enterprise

ensure-pnpm:
	@command -v pnpm || npm install -g pnpm

pre-build: ensure-pnpm
	@mkdir -p $(BUILD_DIR)
	@rsync -av --exclude=$(COMMUNITY_DIR)/build/ --exclude=node_modules/  $(COMMUNITY_DIR) $(BUILD_DIR)
	@rsync -avI --exclude=Makefile --exclude=Dockerfile --exclude=README.md $(ENTERPRISE_DIR) $(BUILD_DIR)
	@$(PM) install --frozen-lockfile -C $(FRONTEND_DIR)

build-enterprise: pre-build
	@$(PM) run -C $(FRONTEND_DIR) build
	@mv $(FRONTEND_DIR)/build $(ENTERPRISE_DIR)/build
	@mv $(FRONTEND_DIR)/node_modules $(ENTERPRISE_DIR)/node_modules
	@mv $(FRONTEND_DIR)/package.json $(ENTERPRISE_DIR)/package.json

CHANGED_FILES =

# The rule to watch the filesystem for changes
watch:
	@fswatch --batch-marker='EOF' -xn ./src ../../frontend | while read file event; do \
		if [ "$$file" = "EOF" ]; then \
			$(MAKE) copy_files CHANGED_FILES="$$list"; \
			list=(); \
		else \
			basename_file="$$(basename "$$file")"; \
			if [[ "$$file" != *~ ]] && [[ ! "$$basename_file" =~ ^[0-9]+$$ ]] && [[ ! "$$basename_file" =~ ^\. ]] && ! git check-ignore -q "$$file"; then \
				echo "Tracking: $$file $$event"; \
				list+=("$$file"); \
			fi; \
		fi; \
	done

copy_files:
	@for file in "$(CHANGED_FILES)"; do \
		if [ -n "$$file" ]; then \
			relative_path="$${file#*/frontend/}"; \
			target_dir="$(FRONTEND_DIR)/$$(dirname "$$relative_path")"; \
			mkdir -p "$$target_dir"; \
			rsync -av "$${file}" "$$target_dir"; \
			echo "Copied $$file to $$target_dir"; \
		fi; \
	done

dev:
	@if [ -z  "$$(ls -A $(FRONTEND_DIR))" ]; then \
		$(MAKE) pre-build; \
	fi; \
	$(PM) -C ${FRONTEND_DIR} run dev & \
	$(MAKE) watch & \
	wait;

clean:
	$(RM) $(ARTIFACTS)
