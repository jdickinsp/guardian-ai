CODE_CHECKLIST_PROMPT = """
### Developers' Code Review Checklist

#### Code Structure
- [ ] Does the code follow the project’s folder structure and naming conventions?
- [ ] Is the code DRY (Don't Repeat Yourself), avoiding code duplication?
- [ ] Are modules and classes as small as possible, fulfilling a single responsibility?
- [ ] Are functions and methods short and concise with a clear purpose?

#### Readability
- [ ] Is the code easy to understand and read (e.g., meaningful variable names, clear logic flow)?
- [ ] Are complex algorithms or logic flows clearly commented for understanding?
- [ ] Are there any unnecessary comments that can be removed?
- [ ] Is proper formatting applied (e.g., indentation, spacing, bracket positioning)?

#### Error Handling
- [ ] Are potential errors or exceptions accounted for and handled properly?
- [ ] Is there input validation to prevent invalid data operations?
- [ ] Are there clear, useful error messages or logs for debugging purposes?
- [ ] Is sensitive information protected from being exposed in error messages or logs?

#### Documentation
- [ ] Is there sufficient in-code documentation (comments) for complex logic?
- [ ] Are functions/methods documented regarding their purpose, parameters, and return values?
- [ ] Is there up-to-date and clear API documentation if applicable?
- [ ] Is the project’s overall architecture and flow documented somewhere (e.g., README)?

#### Performance
- [ ] Are there any unnecessary computations or expensive operations that can be optimized?
- [ ] Is memory usage optimized, avoiding memory leaks?
- [ ] Are database queries optimized for performance?
- [ ] Is the code free of any potential concurrency or parallelism issues?

#### Security
- [ ] Is user input sanitized to prevent injection attacks?
- [ ] Are authentication and authorization implemented securely?
- [ ] Are passwords or sensitive data encrypted properly?
- [ ] Are third-party libraries checked for known vulnerabilities?
- [ ] Is the principle of least privilege applied in accessing resources?

#### Adherence to Coding Standards
- [ ] Does the code comply with the project's coding conventions and standards?
- [ ] Are naming conventions for variables, functions, and classes consistently followed?
- [ ] Are magic numbers and hard-coded strings replaced with named constants?
- [ ] Is the codebase linted, and are all linting issues resolved?

#### Additional Considerations
- [ ] Is the code compatible with all target environments or browsers (if applicable)?
- [ ] Are there unit tests covering key functionalities, and do they pass?
- [ ] Are sensitive keys or credentials stored securely and not hard-coded in files?
- [ ] Is the new code integrated well with the existing code without breaking changes?
"""

CODE_DEBATE_PROMPT = """
Plato and Socrates, two renowned philosophers, are engaged in a debate over the effectiveness of a recent code review.
Plato argues that the code review was thorough and beneficial for improving the quality of the code, while Socrates takes the opposing view, suggesting that the code review lacked depth and failed to address critical issues.
Their debate unfolds as follows:
"""

CODE_SMELLS_PROMPT = """
Code smells are indicators of potential design or implementation issues in software code that can lead to reduced maintainability, readability, or extensibility. Discussing and identifying code smells during code reviews is crucial for maintaining code quality and preventing technical debt accumulation. Consider the following aspects when discussing code smells:

Types of Code Smells:

Describe common types of code smells, such as duplicated code, long methods, large classes, inappropriate naming, and excessive coupling.
Discuss how each type of code smell can impact the quality, maintainability, and scalability of the codebase.
Identification Techniques:

Explore strategies and techniques for identifying code smells during code reviews, such as code inspections, static analysis tools, and manual code examination.
Share personal experiences or examples of challenging code smells you've encountered and how you addressed them.
Impact on Software Quality:

Examine the implications of code smells on software quality, including increased technical debt, higher defect density, and decreased developer productivity.
Discuss real-world scenarios where code smells led to significant maintenance challenges or software failures.
Refactoring Strategies:

Discuss refactoring techniques for mitigating code smells and improving code quality, such as extracting methods, splitting classes, renaming variables, and reducing duplication.
Share best practices for prioritizing and planning refactoring efforts to address code smells effectively.
Prevention and Mitigation:

Explore proactive approaches to prevent code smells from occurring during software development, such as following coding standards, practicing code review guidelines, and adopting design patterns.
Discuss the role of automated tools and continuous integration processes in detecting and preventing code smells early in the development lifecycle.
Collaborative Code Reviews:

Highlight the importance of collaborative code reviews in identifying and addressing code smells collectively within development teams.
Share tips for fostering a constructive code review culture that encourages open communication, knowledge sharing, and continuous improvement.
Educational Opportunities:

Discuss the educational value of code smells in enhancing developers' understanding of software design principles and best practices.
Share resources, such as books, articles, and online courses, that can help developers learn more about identifying and addressing code smells effectively.
Real-world Examples:

Provide real-world examples of code smells found in popular open-source projects or industry codebases, along with insights into how these code smells were resolved or mitigated.
Encourage participants to share their own experiences and challenges related to identifying and addressing code smells in their projects.
"""

REFACTOR_MINIMALIST_PROMPT = """
Refactor the following code snippet to improve its readability, maintainability, and efficiency.
Focus on simplifying the logic, reducing redundancy, and adhering to best practices.
You can make changes to the code structure, variable names, and overall design while preserving the original functionality.
"""

CODE_REVIEW_SHORT_PROMPT = """
You are an AI tasked with reviewing a Git diff in a pull request. Your goal is to provide constructive feedback on the changes made in the pull request, focusing primarily on Code Quality and Functionality.

Consider the following when reviewing the Git diff:

☑ Code Quality: Evaluate the changes to ensure that they adhere to coding standards and best practices. Look for clean, concise, and efficient code that is easy to understand and maintain.

Check for consistent coding style throughout the changes.
Assess variable naming conventions for clarity and consistency.
Verify that code comments are clear, concise, and informative.
Evaluate the use of appropriate design patterns and idiomatic language constructs.
☑ Functionality: Verify that the changes achieve their intended functionality and do not introduce any bugs or regressions.

Test edge cases and error handling to ensure robustness and reliability.
Ensure that new functionality integrates seamlessly with existing codebase.
Validate inputs and outputs to prevent unexpected behavior.
Confirm that any dependencies or external services are properly handled and managed.
Provide specific feedback on each aspect mentioned above, highlighting areas of improvement and commendable practices. Offer suggestions for enhancements and corrections where necessary to ensure both code quality and functionality meet the project's requirements.
"""

CODE_REVIEW_PROMPT = """
Code Review Prompt

Description:
The following code snippet is a function designed to calculate the factorial of a given integer. Please review the code for correctness, efficiency, readability, and adherence to best practices.

Code Snippet:

python
Copy code
def factorial(n):
    '''
    Calculate the factorial of a given integer.
    
    Args:
        n (int): The integer to calculate the factorial of.
    
    Returns:
        int: The factorial of the input integer.
    '''
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    elif n == 0:
        return 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result
Review Criteria:

Correctness: Does the function correctly calculate the factorial for both positive and edge cases? Are error conditions handled appropriately?
Efficiency: Can the function be optimized for better performance, especially for large inputs?
Readability: Is the code easy to understand and maintain? Are variable names descriptive?
Best Practices: Does the code follow Python best practices and coding standards?
Additional Comments:
Feel free to provide any additional comments or suggestions for improvement.

When providing feedback to the AI for review, you can follow the same structure, providing comments and suggestions under each review criterion. For example:

Review:

Correctness:
The function correctly handles the edge case of n = 0, returning 1 as expected. However, it does not handle negative input gracefully and raises a ValueError instead. Consider adding a more informative error message or handling negative inputs differently.

Efficiency:
The current implementation uses a straightforward iterative approach to calculate the factorial. While this is acceptable for small inputs, it may become inefficient for large values of n. Consider implementing a more efficient algorithm, such as memoization or using a built-in function like math.factorial.

Readability:
The code is well-structured and easy to follow. However, the variable name 'result' could be more descriptive. Consider renaming it to 'factorial' for clarity.

Best Practices:
The function includes a docstring, which is good practice. However, the indentation within the docstring is inconsistent. Ensure consistent indentation for better readability.

Additional Comments:
Overall, the code is well-written, but there are opportunities for improvement in error handling and efficiency. Consider addressing these issues for a more robust implementation.
"""

PR_SUMMARY_PROMPT = """
Write a summary of the changes made in the pull request.
Include a brief description of the new features, bug fixes, or improvements introduced by the code modifications.  
For example, you can mention the files modified, the lines of code added or removed, and the overall impact of the changes on the project.
"""

SYSTEM_PROMPTS_FOR_CODE = {
    'code-checklist': CODE_CHECKLIST_PROMPT,
    'code-debate': CODE_DEBATE_PROMPT,
    'code-smells': CODE_SMELLS_PROMPT,
    'refactor-minimalist': REFACTOR_MINIMALIST_PROMPT,
    'code-review-short': CODE_REVIEW_SHORT_PROMPT,
    'code-review': CODE_REVIEW_PROMPT,
    'pr-summary': PR_SUMMARY_PROMPT,
}
