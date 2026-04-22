# Tasks: Microphone Speech Integration

## Task List

- [x] 1. Modify PTTSession to support callbacks
  - [x] 1.1 Add `on_result`, `on_error`, `on_status` parameters to `PTTSession.__init__` with `None` defaults
  - [x] 1.2 Store callbacks as instance attributes
  - [x] 1.3 Call `on_status("Transcribing audio...")` at the start of `process_audio`
  - [x] 1.4 Call `on_status("Normalising query...")` before the LLM processing block
  - [x] 1.5 Call `on_result(self.results)` after `self.results` is populated
  - [x] 1.6 Wrap `process_audio` body in a try/except and call `on_error(exc)` on any exception
  - [x] 1.7 Guard each callback call with `if self.on_xxx is not None` to preserve backward compatibility

- [x] 2. Add `run_pipeline_with_stt_result` to `engine/speech/main.py`
  - [x] 2.1 Define `run_pipeline_with_stt_result(stt_result, on_status, on_result, on_error, country_suffix="my")`
  - [x] 2.2 Extract `dialect`, `question`, `query` from `stt_result`
  - [x] 2.3 Call `on_status("Searching official sources...")` then `find_specific_gov_links(query, country_suffix)`
  - [x] 2.4 Return early via `on_error` if no links are found
  - [x] 2.5 Call `on_status("Extracting web content...")` then `get_chunks_from_list(links)`
  - [x] 2.6 Return early via `on_error` if no chunks are found
  - [x] 2.7 Call `on_status("Indexing content...")` then `ingest_to_chroma(doc_id, all_chunks)`
  - [x] 2.8 Call `on_status("Finding relevant information...")` then `query_from_chroma(question, top_k=5)`
  - [x] 2.9 Call `on_status("Generating answer...")` then `generate_final_response(question, relevant_info, dialect)`
  - [x] 2.10 Call `on_result(final_answer, links, dialect, question)` on success
  - [x] 2.11 Wrap entire function body in try/except; call `on_error(exc)` and return on any exception

- [x] 3. Fix `build_home_view` wiring in `app/views/home.py`
  - [x] 3.1 Update `_get_ptt_session()` to pass `on_result=_on_stt_result`, `on_error=_on_stt_error`, `on_status=_on_stt_status` to `PTTSession(...)`
  - [x] 3.2 Update `_start_recording` to only call `_get_ptt_session().start_recording()` when `active_mode[0] is None`
  - [x] 3.3 Fix `_run_main_pipeline` to call `run_pipeline_with_stt_result` directly (remove reference to non-existent `_pipeline_with_result`)
  - [x] 3.4 Update `_on_stt_result` to reset `is_recording[0]` and mic visuals before calling `_run_main_pipeline`, keeping mic in recording state during pipeline
  - [x] 3.5 Update `on_result` callback inside `_run_main_pipeline` to reset mic visuals after pipeline completes
  - [x] 3.6 Update `on_error` callback inside `_run_main_pipeline` to reset mic visuals on pipeline failure

- [-] 4. Write unit tests
  - [ ] 4.1 Test `PTTSession` can be instantiated with all three callback kwargs
  - [ ] 4.2 Test `run_pipeline_with_stt_result` is importable and callable with correct signature
  - [ ] 4.3 Test `_add_bubble` creates correct widget type for `"user"`, `"bot"`, and `"status"` roles
  - [ ] 4.4 Test `set_mode` toggle: calling `set_mode("document")` twice resets `active_mode[0]` to `None`

- [ ] 5. Write property-based tests (Hypothesis)
  - [ ] 5.1 P7 — `on_result` fires exactly once on success for any valid STT_Result
  - [ ] 5.2 P8 — `on_error` fires exactly once and `on_result` not called when any pipeline step raises
  - [ ] 5.3 P6 — `on_status` is called at least once before each pipeline step for any STT_Result
  - [ ] 5.4 P9 — `find_specific_gov_links` is called with the exact `country_suffix` passed in
  - [ ] 5.5 P10 — PTTSession `on_result` receives dict with `dialect`, `question`, `query` keys for any audio
  - [ ] 5.6 P11 — PTTSession `on_error` called and `on_result` not called when `process_audio` raises
  - [ ] 5.7 P13 — `_add_bubble_safe` increases `chat_list.controls` length by exactly one
  - [ ] 5.8 P2 — `run_pipeline_with_stt_result` is never called when `active_mode[0]` is non-None
  - [ ] 5.9 P3 — mic tap with non-empty chat field calls `on_chat_submit`, not `start_recording`
