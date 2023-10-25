from django.urls import path
from meetings.views import GiteeAuthView, UserInfoView, MeetingsDataView, CreateMeetingView, UpdateMeetingView, \
    DeleteMeetingView, GroupsView, AllMeetingsView, ParticipantsView, LogoutView, LoginView


urlpatterns = [
    path('gitee_login/', GiteeAuthView.as_view()),
    path('user/', UserInfoView.as_view()),
    path('meetingsdata/', MeetingsDataView.as_view()),
    path('meetings/', CreateMeetingView.as_view()),
    path('meeting/action/update/<int:mid>/', UpdateMeetingView.as_view()),
    path('meeting/action/delete/<int:mid>/', DeleteMeetingView.as_view()),
    path('groups/', GroupsView.as_view()),
    path('allmeetings/', AllMeetingsView.as_view()),
    path('participants/<int:mid>/', ParticipantsView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('login/', LoginView.as_view()),
]
