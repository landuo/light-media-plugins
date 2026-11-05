// This review-only command parses source; it never imports or runs the SDK.
package main

import (
	"encoding/json"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strconv"
	"strings"
)

func main() {
	out := []map[string]any{}
	for _, path := range os.Args[1:] {
		if path == "--" {
			continue
		}
		file, err := parser.ParseFile(token.NewFileSet(), path, nil, 0)
		if err != nil {
			panic(err)
		}
		imports := []string{}
		initializers := []string{}
		variables := []string{}
		functions := []string{}
		registrations := []string{}
		for _, spec := range file.Imports {
			value, err := strconv.Unquote(spec.Path.Value)
			if err != nil {
				panic(err)
			}
			imports = append(imports, value)
		}
		for _, decl := range file.Decls {
			switch decl := decl.(type) {
			case *ast.GenDecl:
				if decl.Tok == token.VAR {
					for _, spec := range decl.Specs {
						for _, name := range spec.(*ast.ValueSpec).Names {
							variables = append(variables, name.Name)
						}
					}
				}
			case *ast.FuncDecl:
				functions = append(functions, decl.Name.Name)
				if decl.Name.Name == "init" {
					initializers = append(initializers, decl.Name.Name)
				}
			}
		}
		ast.Inspect(file, func(node ast.Node) bool {
			call, ok := node.(*ast.CallExpr)
			if !ok {
				return true
			}
			var name string
			switch fun := call.Fun.(type) {
			case *ast.Ident:
				name = fun.Name
			case *ast.SelectorExpr:
				name = fun.Sel.Name
			}
			if strings.Contains(strings.ToLower(name), "register") {
				registrations = append(registrations, name)
			}
			return true
		})
		out = append(out, map[string]any{"path": path, "package": file.Name.Name, "imports": imports, "package_variables": variables, "init_functions": initializers, "functions": functions, "registration_calls": registrations})
	}
	if err := json.NewEncoder(os.Stdout).Encode(out); err != nil {
		panic(err)
	}
}
