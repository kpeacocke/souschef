/**
 * @name SousChef Path Sanitizers
 * @description Direct sanitizers for SousChef path validation functions.
 */

private import python
private import semmle.python.ApiGraphs
private import semmle.python.dataflow.new.DataFlow
private import semmle.python.security.dataflow.PathInjectionCustomizations

/**
 * Sanitizer for SousChef path validation functions.
 *
 * These functions (_safe_join, _validated_candidate, _ensure_within_base_path)
 * all perform realpath normalization followed by commonpath containment checks,
 * making them safe as direct sanitizers for path injection.
 */
class SousChefPathSanitizer extends PathInjection::Sanitizer {
  SousChefPathSanitizer() {
    this =
      API::moduleImport("souschef.core.path_utils")
          .getMember(["_safe_join", "_validated_candidate", "_ensure_within_base_path"])
          .getACall()
  }
}
