Dynamic Gravity Processor: Initial Feature Planning Documents

# TODO: Everything

### Project Structure ###
* **dgp**: containing all source and libraries
	* *lib*: containing generic library functions/classes that will be used by the application
	* *ui*: to contain all user interface related code/functionality
* **docs**: containing all documentation built with Sphinx Doc Generator
* **tests**: containing all test suites for the project
	* *context.py* this utility scripts inserts the parent DGP directory into the module 
	search path so that modules can be easily imported for testing
