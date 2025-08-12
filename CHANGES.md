# Breaking Changes

* Introduction of new pipeline API
* Credential and model file
  * Can be yaml or json
  * Can appear anywhere on path from current working directory to root
  * models.json, models.yaml
  * .credentials.json, models.json
* Cases file can be either json or yaml
* Log files
  * Can be either json or yaml.
  * Configuration setting chooses output format.
* .gitignore
  * Be sure to update project .gitignore if using yaml credentials.
  