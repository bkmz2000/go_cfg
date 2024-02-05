package main

import "fmt"

func fact(n int) {
	if n<2 {
		return 1
	}
	return fact(n-1)*n
}

func for_and_if() {
	var x int = 10
	var err = "error"

	for cond {
		x = 20
		if x==10{
			x += 10
			x += 10
		} else {
			x -= 10
		}
	}
}

func conplex_if() {
	var x int = 10
	var err = "error"

	if x > 0 {
		if x==10{
			x += 10
		} else {
			x -= 10
		}
		
		x = 5

		if x==10{
			x += 10
		} 
	} else {
		err = "ok"
	}

}

func fors_ad_ifs(){
		var x int = 10
		var err = "error"
	
		for cond {
			x = 20
			if x==10{
				x += 10
				x += 10
			} else {
				x -= 10
			}
		}
	
		if x > 0 {
			for true {
				for i:=0; i<10; i++{
					if x==10{
						x += 10
					} else {
						x -= 10
					}
					
					x = 5
				}
	
				if x==10{
					x += 10
				} 
			}	
		} else {
			err = "ok"
		}
}


func main() {
	for_and_if()
}