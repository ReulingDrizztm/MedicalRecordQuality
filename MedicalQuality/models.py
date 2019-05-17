from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    用户：绑定角色, 绑定科室
    """
    USER_ID = models.CharField(max_length=30, primary_key=True)  # verbose_name 详细名
    USER_NAME = models.CharField(max_length=30, blank=True)
    EDUCATION_TITLE = models.CharField(max_length=30, blank=True)
    GROUP_CODE = models.CharField(max_length=30, blank=True)
    USER_TYPE = models.CharField(max_length=30, blank=True, null=True)
    IS_ROUNDS = models.CharField(max_length=30, blank=True, null=True)
    LOCKED_TIME = models.DateField(blank=True, null=True)

    role = models.ManyToManyField("RoleAnotherName")
    dept = models.ManyToManyField("Dept")

    def __str__(self):
        return self.username


class Permission(models.Model):
    """
    权限
    """
    title = models.CharField(max_length=128, unique=True)
    url = models.CharField(max_length=128, blank=True)
    interface = models.CharField(max_length=128, blank=True)
    parent = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return '{title}-{url}-{interface}-{parent}'.format(title=self.title,
                                                           url=self.url,
                                                           interface=self.interface,
                                                           parent=self.parent)


class Role(models.Model):
    """
    角色：绑定权限
    """
    ROLE_ID = models.CharField(max_length=32, blank=True)
    ROLE_NAME = models.CharField(max_length=32, blank=True, unique=True)
    PERMISSION_TYPE = models.CharField(max_length=32, blank=True)
    ROLE_PERMISSION_ID = models.CharField(max_length=30, blank=True, null=True)

    permissions = models.ManyToManyField("Permission")
    # 定义角色和权限的多对多关系

    def __str__(self):
        return self.ROLE_NAME


class RoleAnotherName(models.Model):
    """
    角色别名
    """
    ROLE_A_ID = models.CharField(max_length=32, unique=True)
    ROLE_A_NAME = models.CharField(max_length=32, blank=True)
    PERMISSION_A_TYPE = models.CharField(max_length=32, blank=True)
    ROLE_A_PERMISSION_ID = models.CharField(max_length=32, blank=True, null=True)

    role_mrq = models.ForeignKey("Role", null=True, blank=True, on_delete=models.SET_NULL)  # 一对多，此为多

    def __str__(self):
        return self.ROLE_A_NAME


class Dept(models.Model):

    DEPT_CODE = models.CharField(max_length=32, unique=True, primary_key=True)
    DEPT_NAME = models.CharField(max_length=32)
    DEPT_INPUT_CODE = models.CharField(max_length=32, blank=True, null=True)
    DEPT_EMR = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.DEPT_NAME


class District(models.Model):

    WARD_CODE = models.CharField(max_length=32, unique=True, primary_key=True)
    WARD_NAME = models.CharField(max_length=32, unique=True)
    WARD_INPUT_CODE = models.CharField(max_length=32, blank=True, null=True)

    dept = models.ForeignKey("Dept", null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.WARD_NAME
