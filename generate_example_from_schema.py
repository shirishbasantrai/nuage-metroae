#!/usr/bin/env python

import os
import os.path
import sys
import yaml
import jinja2
import argparse

SCHEMA_DIRECTORY = "schemas"


class ExampleFileGenerator(object):
    def __init__(self, no_comments=False, as_template=False, as_example=False,
                 example_folder=None):
        self.has_comments = not no_comments
        self.as_template = as_template | as_example
        self.as_example = as_example
        self.example_folder = example_folder

    def generate_example_from_schema(self, schema_filename):
        self.example_lines = []
        with open(schema_filename, 'r') as file:
            schema = yaml.safe_load(file.read())

        if self.has_comments:
            self.add_example_header(schema)

        self.add_example_content(schema)

        if self.as_example:
            schema_name = os.path.splitext(os.path.basename(
                schema_filename))[0]
            return self.create_example_with_data(schema_name)

        return "\n".join(self.example_lines)

    def create_example_with_data(self, schema_name=""):
        with open(self.example_folder +
                  "/" + schema_name + ".yml", 'r') as example_filename:
            example_yml = yaml.safe_load(example_filename.read())

        template_lines = "\n".join(self.example_lines)
        template = jinja2.Template(template_lines)
        return template.render(**example_yml)

    def add_example_header(self, schema):
        self.example_lines.append("#" * 79)
        if "title" in schema:
            self.example_lines.append("# " + schema["title"])
        if "description" in schema:
            self.example_lines.append("#")
            self.example_lines.append("# " + schema["description"])
        if self.as_template:
            self.example_lines.append("#")
            self.example_lines.append(
                '# Automatically generated by {{ generator_script'
                ' | default("script") }}.')
        self.example_lines.append("#")
        self.example_lines.append("")

    def add_example_content(self, schema):
        is_list = schema["type"] == "array"

        required = list()

        if is_list:
            if "items" in schema and "title" in schema["items"]:
                item_name = schema["items"]["title"]
                if "listName" in schema:
                    list_name = schema["listName"]
                else:
                    list_name = schema["items"]["title"].lower() + "s"
            else:
                item_name = schema["title"][0:-1]
                if "listName" in schema:
                    list_name = schema["listName"]
                else:
                    list_name = schema["title"].lower()
            if self.as_template:
                self.example_lines.append(
                    "{%% if %s is defined and %s %%}" % (list_name,
                                                         list_name))
                self.example_lines.append("{%% for item in %s %%}" % list_name)

            if self.has_comments and "title" in schema:
                item_index = "1"
                if self.as_template:
                    item_index = "{{ loop.index }}"
                self.example_lines.append("#")
                self.example_lines.append("# %s %s" % (item_name,
                                                       item_index))
                self.example_lines.append("#")
            self.example_lines.append("-")
            if "required" in schema["items"]:
                required = schema["items"]["required"]

            self.add_example_fields(schema["items"]["properties"], required,
                                    is_list)

            if self.as_template:
                self.example_lines.append("{% endfor %}")
                self.example_lines.append("{% else %}")
                self.example_lines.append("[ ]")
                self.example_lines.append("{% endif %}")

        else:
            if "required" in schema:
                required = schema["required"]
            self.add_example_fields(schema["properties"], required)

    def add_example_fields(self, field_dict, required, is_list=False):
        for name, field in sorted(field_dict.iteritems(),
                                  key=lambda (k, v): (v["propertyOrder"], k)):

            is_required = name in required
            self.add_example_field(name, field, is_required, is_list)

    def add_example_field(self, name, field, is_required, is_list=False):
        indent = ""

        if is_list:
            indent = "    "

        if self.has_comments:
            if "sectionBegin" in field:
                self.example_lines.append("%s##### %s" % (
                    indent, field["sectionBegin"]))
                self.example_lines.append("")

            if "title" in field:
                self.example_lines.append("%s# < %s >" % (indent,
                                                          field["title"]))

            if "description" in field:
                self.example_lines.append(
                    "%s# %s" % (indent, field["description"]))

            if "enum" in field:
                self.example_lines.append(
                    "%s# (%s) " % (indent, ", ".join(field["enum"])))

            self.example_lines.append("%s#" % indent)

        if not is_required:
            if self.as_template:
                item_name = ""
                if is_list:
                    item_name = "item."

                self.example_lines.append(
                    "%s{%%- if %s%s is defined %%}" % (indent,
                                                       item_name,
                                                       name))

                value = self.get_example_value(name, field, is_list)
                self.example_lines.append("%s%s: %s" % (indent, name,
                                                        value))
                if self.has_comments:
                    self.example_lines.append("%s{%%- else %%}" % indent)

            if self.has_comments:
                default_value = '""'
                if "default" in field and field["default"] != "":
                    default_value = field["default"]
                self.example_lines.append("%s# %s: %s" % (indent,
                                                          name,
                                                          default_value))

            if self.as_template:
                self.example_lines.append("%s{%%- endif %%}" % indent)

        else:
            value = self.get_example_value(name, field, is_list)
            self.example_lines.append("%s%s: %s" % (indent, name, value))

        if self.has_comments:
            self.example_lines.append("")
            if "sectionEnd" in field:
                self.example_lines.append(
                    indent + ("#" * (len(field['sectionEnd']) + 6)))
                self.example_lines.append("")

    def get_example_value(self, name, field, is_list):
        field_type = "string"
        if "type" in field:
            field_type = field["type"]
        if self.as_template:
            is_encrypted = False
            if "encrypt" in field and field["encrypt"] is True:
                is_encrypted = True
            return self.get_example_template_value(name, field_type,
                                                   is_list, is_encrypted)
        else:
            return self.get_example_placeholder_value(field_type)

    def get_example_template_value(self, name, field_type, is_list,
                                   is_encrypted):
        item_name = ""
        if is_list:
            item_name = "item."
        if field_type == "integer":
            return "{{ %s%s }}" % (item_name, name)
        elif field_type == "boolean":
            return "{{ %s%s | lower }}" % (item_name, name)
        elif field_type == "array":
            return ('[ {%% for i in %s%s | default([]) %%}"{{ i }}", '
                    '{%% endfor %%}]' % (item_name, name))
        elif is_encrypted:
            return "{{ %s%s | indent(8, False) }}" % (item_name, name)
        else:
            return '"{{ %s%s }}"' % (item_name, name)

    def get_example_placeholder_value(self, field_type):
        if field_type == "integer":
            return "0"
        elif field_type == "boolean":
            return "false"
        elif field_type == "ipv4":
            return "0.0.0.0"
        elif field_type == "array":
            return "[ ]"
        else:
            return '""'


def main():

    parser = argparse.ArgumentParser(
        description='Generate example from schema')
    parser.add_argument("--schema", help="Schema file name")
    parser.add_argument(
        "--no-comments", dest="no_comments",
        action='store_true', default=False,
        help="Generates without title/usage description comments")
    parser.add_argument(
        "--as-template", dest="as_template", action='store_true',
        default=False, help="Generates as a jinja2 template")
    parser.add_argument(
        "--as-example", dest="as_example", action='store_true', default=False,
        help="Generates a example schema using example data")
    parser.add_argument(
        "--example_data_folder", help="Location of example data folder")
    args = parser.parse_args()

    if not args.schema:
        print "Missing schema name for creating example"
        parser.print_help()
        sys.exit()

    if args.as_example and (args.example_data_folder is None):
        print "Example data folder needed for creating example"
        parser.print_help()
        sys.exit()

    schema_filename = args.schema

    no_comments = args.no_comments
    as_template = args.as_template
    as_example = args.as_example
    example_folder = args.example_data_folder

    generator = ExampleFileGenerator(no_comments, as_template, as_example,
                                     example_folder)

    if schema_filename.find(".") == -1:
        schema_filename = schema_filename + ".json"

    if os.path.isfile(schema_filename):
        print generator.generate_example_from_schema(schema_filename)
        generator.generate_example_from_schema(schema_filename)
    else:
        schema_filename = os.path.join(SCHEMA_DIRECTORY, schema_filename)
        if os.path.isfile(schema_filename):
            generator.generate_example_from_schema(schema_filename)
            print generator.generate_example_from_schema(schema_filename)
        else:
            raise Exception("Could not find schema file %s" % schema_filename)


if __name__ == '__main__':
    main()