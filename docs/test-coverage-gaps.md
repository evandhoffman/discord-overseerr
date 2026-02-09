# Test Coverage Gaps Analysis

## Executive Summary

**Verdict**: ❌ **NOT YET SUITABLE** for general public PR submissions

While the test infrastructure is excellent and core modules have good coverage (71.73% overall), there is a **critical gap** in testing the main user-facing functionality (Discord slash commands), which only has 20% coverage.

## Critical Gaps

### 1. Discord Commands (bot/cogs/movie_commands.py) - 20% Coverage ⚠️

This is the most severe gap. The Discord slash commands are the primary user interface and are almost completely untested.

**Untested Functionality:**
- [ ] `/request` command
  - [ ] Authorization checks
  - [ ] Media search execution
  - [ ] Single result handling
  - [ ] Multiple result dropdown
  - [ ] Media details display
  - [ ] Request button callback
  - [ ] Notification tracking integration
  - [ ] Error handling
- [ ] `/overseerr-health` command
  - [ ] Success case
  - [ ] Connection failure handling
- [ ] `/help` command
  - [ ] Basic help display
  - [ ] Authorization info display
- [ ] `/ping` command (only partially tested)

**Risk**: PRs modifying these commands could easily break core functionality without tests catching it.

### 2. TV Show Support (bot/overseerr.py) - Partially Tested

**Missing Tests:**
- [ ] `get_tv_by_id()` - Not tested at all
- [ ] `request_tv()` - Not tested at all
- [ ] TV show status checking
- [ ] TV show season handling
- [ ] 4K TV show support

**Risk**: TV show requests could be broken and tests wouldn't catch it.

### 3. Additional Coverage Gaps

**bot/overseerr.py** (80.98% - Some gaps):
- [ ] Error recovery paths
- [ ] Network timeout handling
- [ ] Malformed API response handling
- [ ] Session lifecycle edge cases

**bot/notifications.py** (83.51% - Minor gaps):
- [ ] File corruption recovery
- [ ] Concurrent notification handling
- [ ] Cleanup of old notifications

**bot/main.py** (88.30% - Minor gaps):
- [ ] Extension loading failures
- [ ] Command sync edge cases

## Recommended Actions Before Public Release

### Priority 1: Critical (Must Have)

1. **Create comprehensive command tests** (`tests/test_movie_commands.py`)
   ```python
   # Required test coverage:
   - test_ping_command()
   - test_help_command()
   - test_help_with_authorization()
   - test_overseerr_health_success()
   - test_overseerr_health_failure()
   - test_request_unauthorized_user()
   - test_request_authorized_user()
   - test_request_search_no_results()
   - test_request_search_single_result()
   - test_request_search_multiple_results()
   - test_request_media_selection_callback()
   - test_request_show_movie_details()
   - test_request_show_tv_details()
   - test_request_button_callback_success()
   - test_request_button_callback_failure()
   - test_request_wrong_user_interaction()
   - test_request_with_notification_tracking()
   ```

2. **Add TV show operation tests** (to `tests/test_overseerr.py`)
   ```python
   - test_get_tv_by_id()
   - test_get_tv_by_id_4k()
   - test_get_tv_by_id_not_found()
   - test_request_tv_success()
   - test_request_tv_all_seasons()
   - test_request_tv_4k()
   - test_request_tv_quota_exceeded()
   ```

### Priority 2: Important (Should Have)

3. **Add edge case tests for error handling**
   - Network timeouts
   - API rate limiting
   - Malformed responses
   - Concurrent request handling

4. **Add integration tests for TV show workflows**
   - Complete TV show request flow
   - TV show notification flow

### Priority 3: Nice to Have

5. **Increase coverage to 85%+ across all modules**
6. **Add property-based tests** for complex data transformations
7. **Add performance/load tests** for notification system

## Current Coverage Target vs Actual

| Module | Target | Actual | Gap | Priority |
|--------|--------|--------|-----|----------|
| bot/cogs/movie_commands.py | 80% | 20% | -60% | 🔴 CRITICAL |
| bot/overseerr.py | 85% | 81% | -4% | 🟡 MEDIUM |
| bot/notifications.py | 85% | 84% | -1% | 🟢 LOW |
| bot/main.py | 90% | 88% | -2% | 🟢 LOW |
| bot/settings.py | 95% | 95% | 0% | ✅ GOOD |

## Impact Assessment

### What Could Break Without Tests

**Without command tests:**
- Authorization bypass (security risk!)
- Request not actually submitted
- Wrong media requested
- Notifications not triggered
- UI interactions fail silently
- Error messages not shown to users

**Without TV show tests:**
- TV show requests completely broken
- Wrong seasons requested
- 4K TV requests fail
- Status checks incorrect

### What's Protected

✅ Settings loading and validation  
✅ Movie search and request (API level)  
✅ Notification tracking and persistence  
✅ Bot initialization and lifecycle  
✅ Basic error handling  

## Recommendations for PR Guidelines

Until critical gaps are addressed, recommend:

1. **Require tests for all new commands**
2. **PRs to movie_commands.py require corresponding tests**
3. **Manual testing checklist** for Discord interactions
4. **Protected main branch** with required reviews
5. **CI must pass** before merge

## Timeline to PR-Ready

**Estimated effort**: 8-12 hours

- Priority 1 tasks: 6-8 hours
- Priority 2 tasks: 2-4 hours

**Minimum viable**: Complete Priority 1 tasks to reach ~80% coverage and protect critical user-facing functionality.

## Conclusion

The test infrastructure is **excellent** and the foundation is solid, but the **critical gap in Discord command testing** makes this project **not yet ready** for public PR submissions.

**Recommendation**: Complete Priority 1 tasks (add comprehensive command tests and TV show tests) before opening to public contributions. This will:

1. Protect critical user-facing functionality
2. Give contributors confidence their PRs won't break things
3. Provide examples of how to test Discord interactions
4. Catch regressions early in CI/CD

Once Priority 1 is complete, the project will be in good shape for public contributions with clear testing expectations.
