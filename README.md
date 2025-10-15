# Linear Elastostatics Extension for XLB

This repository was **forked from [XLB](https://github.com/XLB)** and extended to include a **solver for linear elastostatics**.  
Additionally, it implements a **multigrid Lattice Boltzmann (LB) scheme** for linear elastostatics.

---

## 🧩 Overview

All newly implemented code is located in:

`xlb/experimental/multigrid_elastostatics`


- Files related to the **original LB scheme** use the prefix:  

`solid_*`

- Files related to the **multigrid LB scheme** use the prefix:  

`multigrid_*`


> 📚 A full documentation is not yet available.  
> However, most functions include detailed **docstrings** explaining their purpose and parameters.

---

## 🧪 Numerical Experiments

Validation and analysis scripts can be found in the `numerical_experiments/` directory.  
They include studies on:

- Convergence of both the original and multigrid LB methods  
- Smoothing properties of the LB scheme  
- Stability of the multigrid LB solver  
- Accuracy of convergence speed predictions

Each experiment resides in its respective subfolder.

---

## 🚀 Running the Schemes

To run the original or multigrid LB schemes, check out the usage examples in:

`examples/multigrid_elastostatics`


These scripts demonstrate typical simulation setups and parameter configurations.

---

## 📄 Notes

- This repository builds upon the core structure of XLB.  
- The focus of this extension is on **linear elastostatics** and **multigrid acceleration**.  
- Contributions and feedback are welcome!